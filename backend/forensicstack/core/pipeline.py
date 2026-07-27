"""
Analysis orchestrator: identity → plan → run → normalize.

This is the single place that knows how a job goes from "a file on disk" to
"a list of findings".  Previously that logic was smeared across ``worker.py``,
``docker_executor.py`` and ``normalization_engine.py``, with each layer holding
part of the state and no layer owning the whole.

Design notes
------------

* **Every job gets its own workspace**, created here and destroyed here.  The
  container never sees anything outside it, and cleanup is a single ``rmtree``
  in a ``finally`` — not a best-effort ``except: pass`` scattered over three
  functions.
* **Failures are typed.**  ``ToolUnavailableError`` (retryable infrastructure)
  is distinct from ``ToolExecutionError`` (this input, this tool, terminal).
  The old worker had one catch-all that turned "MinIO was briefly down" and
  "this file is garbage" into the same ``status=failed``.
* **Normalizers are adapted, not rewritten.**  A normalizer that still returns
  the v1 dataclass is upgraded through ``Finding.from_legacy``, so the migration
  can happen one tool at a time.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Sequence

from forensicstack.core.findings.finding import Finding
from forensicstack.core.plugins.manifest import FeatureSpec, PluginManifest
from forensicstack.core.plugins.registry import PluginRegistry, registry as default_registry
from forensicstack.core.runners.base import (
    JobWorkspace,
    RunResult,
    ToolError,
    ToolExecutionError,
    ToolTimeoutError,
    ToolUnavailableError,
)
from forensicstack.core.runners.docker import DockerRunner, default_runner_for
from forensicstack.core.triage.identify import ArtifactIdentity, identify
from forensicstack.core.triage.kinds import FindingKind
from forensicstack.core.triage.router import AnalysisPlan, plan_for

log = logging.getLogger(__name__)

#: Hard ceiling on findings kept per job.  A single `$MFT` parse yields millions
#: of rows; the old code json.dumps'd all of them into one Redis hash field and
#: returned the lot in one HTTP response.
MAX_FINDINGS_PER_JOB = 50_000


@dataclass
class JobOutcome:
    job_id: str
    tool: str
    feature: str
    status: str                       # completed | failed
    findings: list[Finding] = field(default_factory=list)
    error: str | None = None
    error_kind: str | None = None
    retryable: bool = False
    duration_s: float = 0.0
    output_dir: str | None = None
    truncated: bool = False
    stderr_excerpt: str | None = None

    def summary(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "tool": self.tool,
            "feature": self.feature,
            "status": self.status,
            "findings": len(self.findings),
            "truncated": self.truncated,
            "duration_s": round(self.duration_s, 2),
            "error": self.error,
            "error_kind": self.error_kind,
            "retryable": self.retryable,
        }


class AnalysisPipeline:
    def __init__(
        self,
        workspace_root: Path,
        *,
        reg: PluginRegistry | None = None,
        runner_factory: Callable[[PluginManifest], Any] | None = None,
    ) -> None:
        self.workspace_root = Path(workspace_root)
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.registry = reg or default_registry
        self._runner_factory = runner_factory or default_runner_for

    # ---- identification & planning ----------------------------------------- #

    def identify(self, path: Path, *, original_filename: str | None = None) -> ArtifactIdentity:
        return identify(path, original_filename=original_filename)

    def plan(self, ident: ArtifactIdentity, **kwargs) -> AnalysisPlan:
        return plan_for(ident, reg=self.registry, **kwargs)

    # ---- execution ---------------------------------------------------------- #

    def run_job(
        self,
        job_id: str,
        tool: str,
        feature_id: str | None,
        input_path: Path,
        *,
        artifact_sha256: str | None = None,
        keep_workspace: bool = False,
    ) -> JobOutcome:
        """Execute one (tool, feature) against one artifact.

        Never raises for tool-level failures — the outcome carries the error, so
        the caller can decide about retries without unwinding a stack.
        """
        started = time.monotonic()
        outcome = JobOutcome(job_id=job_id, tool=tool, feature=feature_id or "", status="failed")
        workspace: JobWorkspace | None = None

        try:
            manifest, feature = self.registry.resolve(tool, feature_id)
            outcome.feature = feature.id

            workspace = JobWorkspace.create(self.workspace_root, job_id)
            staged = workspace.place_input(Path(input_path))

            runner = self._runner_factory(manifest)
            result: RunResult = runner.run(manifest, feature, workspace, staged)

            findings = self._normalize(manifest, feature, result,
                                       job_id=job_id, artifact_sha256=artifact_sha256)
            if len(findings) > MAX_FINDINGS_PER_JOB:
                outcome.truncated = True
                findings = findings[:MAX_FINDINGS_PER_JOB]
                findings.append(
                    Finding(
                        job_id=job_id, tool=tool, feature=feature.id,
                        artifact_sha256=artifact_sha256,
                        kind=FindingKind.ERROR, severity="low",
                        title=f"result truncated at {MAX_FINDINGS_PER_JOB} findings",
                        data={"limit": MAX_FINDINGS_PER_JOB},
                    )
                )

            outcome.findings = findings
            outcome.status = "completed"
            outcome.output_dir = str(result.output_dir)

        except ToolError as exc:
            outcome.error = str(exc)
            outcome.error_kind = type(exc).__name__
            outcome.retryable = getattr(exc, "retryable", False)
            if isinstance(exc, ToolExecutionError):
                outcome.stderr_excerpt = (exc.stderr or "")[-2000:]
            log.warning("job %s (%s/%s) failed: %s", job_id, tool, feature_id, exc)
        except Exception as exc:  # noqa: BLE001 — last resort, must not kill the worker
            outcome.error = f"{type(exc).__name__}: {exc}"
            outcome.error_kind = "InternalError"
            log.exception("job %s (%s/%s) crashed", job_id, tool, feature_id)
        finally:
            outcome.duration_s = time.monotonic() - started
            if workspace and not keep_workspace:
                workspace.cleanup()

        return outcome

    # ---- normalization ------------------------------------------------------ #

    def _normalize(
        self,
        manifest: PluginManifest,
        feature: FeatureSpec,
        result: RunResult,
        *,
        job_id: str,
        artifact_sha256: str | None,
    ) -> list[Finding]:
        normalizer = self.registry.normalizer(manifest.id)

        try:
            raw = self._call_normalizer(
                normalizer, result.output_dir,
                job_id=job_id, artifact_sha256=artifact_sha256,
                tool_version=manifest.version,
            )
        except Exception as exc:  # noqa: BLE001
            # A normalizer crash must not discard a successful tool run: report
            # it as a finding so the raw output is still reachable in storage.
            log.exception("normalizer for %s failed", manifest.id)
            return [
                Finding(
                    job_id=job_id, tool=manifest.id, tool_version=manifest.version,
                    feature=feature.id, artifact_sha256=artifact_sha256,
                    kind=FindingKind.ERROR, severity="high",
                    title=f"normalizer failed: {type(exc).__name__}",
                    data={
                        "error": str(exc),
                        "output_files": [p.name for p in result.produced_files][:50],
                    },
                )
            ]

        return [self._coerce(f, manifest, feature, job_id, artifact_sha256) for f in raw]

    @staticmethod
    def _call_normalizer(normalizer, output_dir: Path, **kwargs) -> Sequence[Any]:
        """Call a normalizer, tolerating both the v1 and v2 signatures.

        v1 normalizers are ``normalize(output_dir)``; v2 ones accept provenance
        keyword arguments. Try the richer call first and fall back, so both
        generations coexist during the migration.
        """
        try:
            return normalizer.normalize(output_dir, **kwargs) or []
        except TypeError as exc:
            if "unexpected keyword" not in str(exc) and "positional" not in str(exc):
                raise
            return normalizer.normalize(output_dir) or []

    @staticmethod
    def _coerce(
        item: Any,
        manifest: PluginManifest,
        feature: FeatureSpec,
        job_id: str,
        artifact_sha256: str | None,
    ) -> Finding:
        if isinstance(item, Finding):
            if not item.job_id:
                item.job_id = job_id
            if not item.artifact_sha256:
                item.artifact_sha256 = artifact_sha256
            if not item.tool_version:
                item.tool_version = manifest.version
            if not item.feature:
                item.feature = feature.id
            return item
        upgraded = Finding.from_legacy(item, job_id=job_id)
        upgraded.tool_version = manifest.version
        upgraded.feature = feature.id
        upgraded.artifact_sha256 = artifact_sha256
        return upgraded


__all__ = [
    "AnalysisPipeline",
    "JobOutcome",
    "MAX_FINDINGS_PER_JOB",
    "ToolExecutionError",
    "ToolTimeoutError",
    "ToolUnavailableError",
    "DockerRunner",
]
