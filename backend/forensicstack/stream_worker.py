"""
Queue worker (Redis Streams).

Supersedes ``forensicstack/worker.py``. Both can run side by side during the
migration: the old one drains the legacy ``job_queue`` list, this one consumes
the ``jobs:stream`` consumer group. Point ``docker-compose`` at
``python -m forensicstack.stream_worker`` when you are ready to switch.

What is different from the old loop
-----------------------------------

``worker.py`` was a single ``while True`` over a blocking ``brpop`` calling a
blocking ``subprocess.run``: one job at a time, process-wide. A Volatility job
with a 7200 s timeout blocked the entire queue for two hours, and there was no
concurrency knob at any layer.

Here, N in-process workers each hold their own lease. Crash safety comes from
the consumer group rather than from hope: an unacked message is reclaimed after
the visibility timeout instead of being lost with the process.

Run:
    python -m forensicstack.stream_worker --concurrency 4
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from forensicstack.core.pipeline import AnalysisPipeline, JobOutcome
from forensicstack.core.plugins.registry import registry
from forensicstack.core.queue import JobQueue, Lease

log = logging.getLogger("forensicstack.worker")

_BACKEND_DIR = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = Path(
    os.getenv("FORENSICSTACK_WORKSPACE", str(_BACKEND_DIR / "tmp_jobs" / "work"))
)

#: Age after which an orphaned workspace is swept, in seconds.
STALE_WORKSPACE_S = int(os.getenv("FORENSICSTACK_STALE_WORKSPACE_S", str(24 * 3600)))

_shutdown = threading.Event()


def _install_signal_handlers() -> None:
    def handler(signum, _frame):
        log.info("received signal %s — finishing current jobs then exiting", signum)
        _shutdown.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, handler)
        except (ValueError, OSError):  # pragma: no cover - non-main thread
            pass


def _sweep_workspaces(root: Path) -> int:
    """Remove abandoned job directories.

    The old cleanup ran only on the idle path, roughly every 50 empty polls, so
    a continuously busy worker never garbage-collected anything and `tmp_jobs`
    grew without bound. Here it runs on a timer regardless of load.
    """
    if not root.is_dir():
        return 0
    cutoff = time.time() - STALE_WORKSPACE_S
    removed = 0
    for child in root.iterdir():
        try:
            if child.is_dir() and child.stat().st_mtime < cutoff:
                import shutil

                shutil.rmtree(child, ignore_errors=True)
                removed += 1
        except OSError:
            continue
    if removed:
        log.info("swept %d stale workspace(s)", removed)
    return removed


class Worker:
    def __init__(self, concurrency: int = 2) -> None:
        self.queue = JobQueue()
        self.pipeline = AnalysisPipeline(WORKSPACE_ROOT, reg=registry)
        self.concurrency = max(1, concurrency)
        self._inflight = threading.Semaphore(self.concurrency)

    # ---- one job ------------------------------------------------------------ #

    def handle(self, lease: Lease) -> None:
        job = lease.job
        try:
            self.queue.set_status(
                job.job_id, "running",
                tool=job.tool, feature=job.feature or "",
                attempt=str(lease.delivery_count),
                started_at=str(time.time()),
            )
            if job.plan_id:
                self.queue.r.sadd(f"plan:{job.plan_id}:jobs", job.job_id)
                self.queue.r.expire(f"plan:{job.plan_id}:jobs", 14 * 24 * 3600)

            outcome: JobOutcome = self.pipeline.run_job(
                job_id=job.job_id,
                tool=job.tool,
                feature_id=job.feature,
                input_path=Path(job.input_path),
                artifact_sha256=job.artifact_sha256,
            )

            if outcome.status == "failed" and outcome.retryable \
                    and lease.delivery_count < 3:
                # Infrastructure hiccup: leave the message unacked so it is
                # redelivered rather than burning the job. The old worker had
                # one catch-all that made "MinIO was down" terminal.
                self.queue.set_status(
                    job.job_id, "queued",
                    error=outcome.error or "",
                    error_kind=outcome.error_kind or "",
                    note="retryable failure, will be redelivered",
                )
                self.queue.retry_later(lease)
                return

            self._persist(job, outcome)
            self.queue.ack(lease)

        except Exception as exc:  # noqa: BLE001 - a worker must never die on one job
            log.exception("unhandled error on job %s", job.job_id)
            self.queue.set_status(job.job_id, "failed",
                                  error=f"{type(exc).__name__}: {exc}")
            self.queue.ack(lease)
        finally:
            self._inflight.release()

    def _persist(self, job, outcome: JobOutcome) -> None:
        """Record the outcome.

        Findings are summarised into Redis and written in full to the job's
        result file. They are deliberately *not* json.dumps'd into a Redis hash
        field the way the old worker did — an `$MFT` parse produces millions of
        rows, and Redis is a queue, not the system of record for evidence.
        """
        results_dir = WORKSPACE_ROOT.parent / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        result_path = results_dir / f"{job.job_id}.json"

        payload = {
            "job": {
                "job_id": job.job_id,
                "tool": job.tool,
                "feature": outcome.feature,
                "plan_id": job.plan_id,
                "case_id": job.case_id,
                "user_id": job.user_id,
                "artifact_sha256": job.artifact_sha256,
            },
            "outcome": outcome.summary(),
            "findings": [f.to_row() for f in outcome.findings],
        }
        try:
            result_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError as exc:
            log.error("could not write results for %s: %s", job.job_id, exc)

        by_severity: dict[str, int] = {}
        by_kind: dict[str, int] = {}
        for f in outcome.findings:
            by_severity[f.severity] = by_severity.get(f.severity, 0) + 1
            by_kind[f.kind.value] = by_kind.get(f.kind.value, 0) + 1

        self.queue.set_status(
            job.job_id,
            outcome.status,
            finished_at=str(time.time()),
            duration_s=str(round(outcome.duration_s, 2)),
            finding_count=str(len(outcome.findings)),
            truncated=str(outcome.truncated).lower(),
            result_path=str(result_path),
            error=outcome.error or "",
            error_kind=outcome.error_kind or "",
            summary={"by_severity": by_severity, "by_kind": by_kind},
        )
        log.info("job %s %s: %s", job.job_id, outcome.status, outcome.summary())

    # ---- loop --------------------------------------------------------------- #

    def run(self) -> int:
        log.info(
            "worker %s starting: concurrency=%d workspace=%s plugins=%s",
            self.queue.consumer, self.concurrency, WORKSPACE_ROOT,
            ", ".join(registry.ids),
        )
        last_sweep = 0.0
        with ThreadPoolExecutor(max_workers=self.concurrency,
                                thread_name_prefix="fs-job") as pool:
            while not _shutdown.is_set():
                if time.time() - last_sweep > 3600:
                    _sweep_workspaces(WORKSPACE_ROOT)
                    last_sweep = time.time()

                # Block a slot before reserving, so we never hold a lease we
                # have no capacity to run.
                if not self._inflight.acquire(timeout=1.0):
                    continue
                try:
                    lease = self.queue.reserve(block_ms=2000)
                except Exception as exc:  # noqa: BLE001 - Redis blip
                    self._inflight.release()
                    log.warning("queue unavailable (%s), retrying in 5s", exc)
                    _shutdown.wait(5)
                    continue

                if lease is None:
                    self._inflight.release()
                    continue
                pool.submit(self.handle, lease)

            log.info("draining in-flight jobs…")
        log.info("worker stopped")
        return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ForensicStack queue worker")
    parser.add_argument(
        "--concurrency", type=int,
        default=int(os.getenv("FORENSICSTACK_CONCURRENCY", "2")),
        help="jobs to run in parallel in this process",
    )
    parser.add_argument("--log-level", default=os.getenv("LOG_LEVEL", "INFO"))
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )
    _install_signal_handlers()

    try:
        registry.load()
    except Exception as exc:  # noqa: BLE001
        log.error("plugin manifests are invalid, refusing to start:\n%s", exc)
        return 2

    return Worker(concurrency=args.concurrency).run()


if __name__ == "__main__":
    sys.exit(main())
