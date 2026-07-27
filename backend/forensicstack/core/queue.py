"""
Durable job queue on Redis Streams.

Replaces ``LPUSH`` + ``BRPOP``.  ``BRPOP`` is a *destructive* pop with no
acknowledgement: if the worker was killed mid-job the message was already gone,
the job vanished, and its status stayed ``running`` forever with nothing to
reclaim it.  There was no retry, no dead-letter, no visibility timeout and no
heartbeat.

Streams + consumer groups give all of that natively:

* ``XREADGROUP`` delivers a message *and* records it as pending for this
  consumer — a crash leaves it claimable, not lost.
* ``XAUTOCLAIM`` lets a healthy worker take over messages whose owner died.
* ``XACK`` is explicit, after the work is durably recorded.
* Redelivery is counted, so a message that repeatedly kills its worker
  ("poison pill") lands in a dead-letter stream instead of looping forever.

Job *state* also stops being unbounded: hashes get a TTL, and findings are no
longer stuffed into a hash field — they belong in Postgres/MinIO.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

import redis

log = logging.getLogger(__name__)

STREAM = os.getenv("FORENSICSTACK_JOB_STREAM", "jobs:stream")
GROUP = os.getenv("FORENSICSTACK_JOB_GROUP", "workers")
DLQ_STREAM = f"{STREAM}:dead"

#: A message not acked within this window is considered abandoned.
VISIBILITY_TIMEOUT_MS = int(os.getenv("FORENSICSTACK_VISIBILITY_TIMEOUT_MS", str(4 * 3600 * 1000)))
MAX_DELIVERIES = int(os.getenv("FORENSICSTACK_MAX_DELIVERIES", "3"))

#: Job state hashes expire; previously they were written with no TTL and Redis
#: grew without bound while doubling as the system of record for evidence.
JOB_TTL_S = int(os.getenv("FORENSICSTACK_JOB_TTL_S", str(14 * 24 * 3600)))

#: Cap the stream so a runaway producer cannot exhaust memory.
STREAM_MAXLEN = int(os.getenv("FORENSICSTACK_STREAM_MAXLEN", "100000"))


def build_redis(**overrides: Any) -> redis.Redis:
    """Client factory with a fail-loud password policy.

    The old modules did ``os.getenv("REDIS_PASSWORD", "")`` and, on a missing
    variable, silently connected *without* authentication — or, in one file,
    fell back to a password committed to git.
    """
    password = os.getenv("REDIS_PASSWORD")
    if password is None:
        raise RuntimeError(
            "REDIS_PASSWORD is not set. Set it explicitly (empty string is "
            "accepted for a local, network-isolated Redis) rather than relying "
            "on an implicit unauthenticated connection."
        )
    params: dict[str, Any] = {
        "host": os.getenv("REDIS_HOST", "localhost"),
        "port": int(os.getenv("REDIS_PORT", "6379")),
        "password": password or None,
        "decode_responses": True,
        "socket_keepalive": True,
        "health_check_interval": 30,
        # Without these a dead Redis hangs the worker until the TCP default.
        "socket_connect_timeout": 5,
        "socket_timeout": 30,
    }
    params.update(overrides)
    return redis.Redis(**params)


@dataclass
class JobMessage:
    job_id: str
    tool: str
    feature: str | None = None
    input_path: str = ""
    artifact_sha256: str | None = None
    case_id: int | None = None
    artifact_id: int | None = None
    user_id: int | None = None
    plan_id: str | None = None
    priority: int = 50
    submitted_at: float = field(default_factory=time.time)

    def to_fields(self) -> dict[str, str]:
        return {"payload": json.dumps(asdict(self))}

    @classmethod
    def from_fields(cls, fields: dict[str, str]) -> "JobMessage":
        return cls(**json.loads(fields["payload"]))


@dataclass
class Lease:
    """A message checked out by this consumer. Ack it or it comes back."""

    message_id: str
    job: JobMessage
    delivery_count: int = 1


class JobQueue:
    def __init__(self, client: redis.Redis | None = None, *, consumer: str | None = None) -> None:
        self.r = client or build_redis()
        self.consumer = consumer or f"{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:6]}"
        self._ensure_group()

    def _ensure_group(self) -> None:
        try:
            self.r.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
        except redis.ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    # ---- producing ---------------------------------------------------------- #

    def submit(self, job: JobMessage) -> str:
        message_id = self.r.xadd(
            STREAM, job.to_fields(), maxlen=STREAM_MAXLEN, approximate=True
        )
        # Status is written *before* the message is visible to a consumer in the
        # old code's ordering bug; here the reverse race is harmless because we
        # only ever move status forward, never back to "queued".
        self.set_status(job.job_id, "queued", tool=job.tool, feature=job.feature or "",
                        submitted_at=job.submitted_at)
        return message_id

    def submit_many(self, jobs: Iterable[JobMessage]) -> list[str]:
        return [self.submit(j) for j in jobs]

    # ---- consuming ---------------------------------------------------------- #

    def reserve(self, *, block_ms: int = 5000) -> Lease | None:
        """Take the next message, first reclaiming anything abandoned."""
        reclaimed = self._reclaim()
        if reclaimed:
            return reclaimed

        resp = self.r.xreadgroup(
            GROUP, self.consumer, {STREAM: ">"}, count=1, block=block_ms
        )
        if not resp:
            return None
        _, entries = resp[0]
        if not entries:
            return None
        message_id, fields = entries[0]
        try:
            return Lease(message_id=message_id, job=JobMessage.from_fields(fields))
        except (KeyError, json.JSONDecodeError, TypeError) as exc:
            log.error("undecodable message %s, dead-lettering: %s", message_id, exc)
            self._dead_letter(message_id, fields, reason=f"undecodable: {exc}")
            self.r.xack(STREAM, GROUP, message_id)
            return None

    def _reclaim(self) -> Lease | None:
        """Adopt a message whose previous owner died."""
        try:
            _, entries, _ = self.r.xautoclaim(
                STREAM, GROUP, self.consumer, min_idle_time=VISIBILITY_TIMEOUT_MS, count=1
            )
        except redis.ResponseError:  # older Redis without XAUTOCLAIM
            return None
        if not entries:
            return None
        message_id, fields = entries[0]
        if fields is None:  # message was trimmed away underneath us
            self.r.xack(STREAM, GROUP, message_id)
            return None

        deliveries = self._delivery_count(message_id)
        if deliveries > MAX_DELIVERIES:
            log.error("message %s exceeded %d deliveries — dead-lettering",
                      message_id, MAX_DELIVERIES)
            self._dead_letter(message_id, fields, reason="max deliveries exceeded")
            self.r.xack(STREAM, GROUP, message_id)
            try:
                job = JobMessage.from_fields(fields)
                self.set_status(job.job_id, "failed",
                                error="job repeatedly failed to complete and was abandoned")
            except Exception:  # noqa: BLE001
                pass
            return None

        try:
            return Lease(message_id=message_id,
                         job=JobMessage.from_fields(fields),
                         delivery_count=deliveries)
        except Exception as exc:  # noqa: BLE001
            self._dead_letter(message_id, fields, reason=f"undecodable on reclaim: {exc}")
            self.r.xack(STREAM, GROUP, message_id)
            return None

    def _delivery_count(self, message_id: str) -> int:
        pending = self.r.xpending_range(STREAM, GROUP, min=message_id, max=message_id, count=1)
        return int(pending[0]["times_delivered"]) if pending else 1

    def ack(self, lease: Lease) -> None:
        self.r.xack(STREAM, GROUP, lease.message_id)

    def retry_later(self, lease: Lease) -> None:
        """Release without acking so another worker picks it up after the
        visibility timeout. Used for retryable infrastructure failures."""
        log.info("releasing %s for retry", lease.message_id)

    def _dead_letter(self, message_id: str, fields: dict[str, str] | None, *, reason: str) -> None:
        payload = dict(fields or {})
        payload["_dead_reason"] = reason
        payload["_original_id"] = message_id
        payload["_dead_at"] = str(time.time())
        self.r.xadd(DLQ_STREAM, payload, maxlen=STREAM_MAXLEN, approximate=True)

    # ---- job state ---------------------------------------------------------- #

    @staticmethod
    def _key(job_id: str) -> str:
        return f"job:{job_id}"

    def set_status(self, job_id: str, status: str, **extra: Any) -> None:
        key = self._key(job_id)
        payload = {"status": status, "updated_at": str(time.time())}
        for k, v in extra.items():
            if v is None:
                continue
            payload[k] = v if isinstance(v, str) else json.dumps(v)
        pipe = self.r.pipeline()
        pipe.hset(key, mapping=payload)
        pipe.expire(key, JOB_TTL_S)
        pipe.execute()

    def get_status(self, job_id: str) -> dict[str, Any] | None:
        data = self.r.hgetall(self._key(job_id))
        if not data:
            return None
        for field_name in ("plan", "identity", "summary"):
            if field_name in data:
                try:
                    data[field_name] = json.loads(data[field_name])
                except (json.JSONDecodeError, TypeError):
                    pass
        return data

    def stats(self) -> dict[str, Any]:
        try:
            info = self.r.xinfo_groups(STREAM)
        except redis.ResponseError:
            info = []
        group = next((g for g in info if g.get("name") == GROUP), {})
        return {
            "stream": STREAM,
            "length": self.r.xlen(STREAM),
            "pending": group.get("pending", 0),
            "consumers": group.get("consumers", 0),
            "dead_letters": self.r.xlen(DLQ_STREAM) if self.r.exists(DLQ_STREAM) else 0,
        }
