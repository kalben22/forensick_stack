"""
Finding v2 — the record every tool normalises into.

Why v1 had to change
--------------------

v1 was ``@dataclass Finding(tool, artifact_type, source, timestamp, data,
confidence)``.  It was an *envelope*, not a schema, and nothing was enforced:

* ``timestamp`` was a raw string in whatever format the tool emitted — and two
  of the five normalizers hardcoded ``timestamp=None`` unconditionally, including
  for ``windows.netscan`` (which carries ``Created``) and for MFT/EVTX CSVs whose
  entire value *is* timestamps.  A forensic timeline product was discarding every
  timestamp at the normalisation boundary.
* ``source`` meant four different things depending on the normalizer
  (``"memory"``, ``"filesystem"``, a CSV stem, an absolute host path), so
  cross-tool correlation was impossible.
* ``confidence`` was a per-normalizer magic constant (0.4 / 0.6 / 0.7 / 0.85)
  with no derivation and no documented meaning.
* There was no provenance at all: no source path inside the artifact, no tool
  version, no artifact hash — the things a finding needs to be defensible.

v2 closes the vocabulary (:class:`FindingKind`), makes time a real
``datetime`` in UTC with a stated meaning (``ts_kind``), and carries provenance.
``data`` stays free-form; the structure *around* it does not.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from forensicstack.core.triage.kinds import FindingKind

Severity = Literal["info", "low", "medium", "high", "critical"]
TimestampKind = Literal["created", "modified", "accessed", "changed", "observed", "logged", "deleted"]


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    job_id: str | None = None

    # ---- provenance -------------------------------------------------------- #
    tool: str
    tool_version: str = ""
    feature: str = ""
    artifact_sha256: str | None = None
    source_path: str | None = None
    """Path *inside* the artifact (e.g. the CSV or SQLite file iLEAPP parsed),
    never a host path — host paths in findings leak worker layout to the API."""
    source_offset: int | None = None

    # ---- semantics --------------------------------------------------------- #
    kind: FindingKind = FindingKind.LOG_EVENT
    ts_utc: datetime | None = None
    ts_kind: TimestampKind | None = None
    ts_precision: Literal["s", "ms", "us", "ns"] | None = None

    # ---- payload ----------------------------------------------------------- #
    title: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    labels: list[str] = Field(default_factory=list)
    severity: Severity = "info"

    @field_validator("ts_utc")
    @classmethod
    def _force_utc(cls, v: datetime | None) -> datetime | None:
        """A naive datetime in a forensic record is a bug waiting to happen.

        v1 mixed naive ``datetime.utcnow()`` columns with tz-aware values from
        the API layer. Everything here is UTC-aware or None.
        """
        if v is None:
            return None
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)

    @field_serializer("ts_utc")
    def _ser_ts(self, v: datetime | None) -> str | None:
        return v.isoformat() if v else None

    @field_serializer("id")
    def _ser_id(self, v: uuid.UUID) -> str:
        return str(v)

    # ---- interop ----------------------------------------------------------- #

    @classmethod
    def from_legacy(cls, legacy: Any, *, job_id: str | None = None) -> "Finding":
        """Adapt a v1 ``Finding`` dataclass so existing normalizers keep working.

        Lets the platform migrate one normalizer at a time instead of requiring
        a flag-day rewrite of all five.
        """
        from forensicstack.core.findings.timeparse import (
            map_artifact_type,
            parse_timestamp,
        )

        raw_ts = getattr(legacy, "timestamp", None)
        ts, precision = parse_timestamp(raw_ts) if raw_ts else (None, None)
        kind = map_artifact_type(
            getattr(legacy, "tool", ""), getattr(legacy, "artifact_type", "")
        )
        return cls(
            job_id=job_id,
            tool=getattr(legacy, "tool", "unknown"),
            feature=getattr(legacy, "artifact_type", "") or "",
            source_path=getattr(legacy, "source", None),
            kind=kind,
            ts_utc=ts,
            ts_kind="observed" if ts else None,
            ts_precision=precision,
            data=dict(getattr(legacy, "data", {}) or {}),
            severity="info",
        )

    def to_row(self) -> dict[str, Any]:
        """Flat dict for persistence / API responses."""
        return self.model_dump(mode="json")

    def summary(self) -> str:
        if self.title:
            return self.title
        for key in ("name", "process", "path", "url", "value", "message"):
            if key in self.data:
                return f"{self.kind.value}: {self.data[key]}"
        return self.kind.value
