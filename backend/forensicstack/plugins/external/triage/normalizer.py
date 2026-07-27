"""
Normalizer for the triage scanner.

Reference implementation for the manifest-based plugin system: it lives next to
its own Dockerfile and plugin.yaml, is imported lazily by dotted path, and emits
Finding v2 directly.

It is also deliberately defensive about its own tool's output. The old
``ExiftoolNormalizer`` did a bare ``json.loads(file.read_text())`` with no
try/except, so truncated output raised ``JSONDecodeError`` inside ``normalize()``
and failed the job *after* the tool had succeeded.
"""

from __future__ import annotations

import json
from pathlib import Path

from forensicstack.core.findings.finding import Finding
from forensicstack.core.triage.kinds import FindingKind

#: String classes that justify raising severity above "info" on their own.
_NOTABLE = {
    "private_key": "high",
    "aws_key": "high",
    "jwt": "medium",
    "onion": "medium",
    "powershell": "medium",
    "bitcoin_address": "low",
    "url": "low",
    "ipv4": "low",
    "ipv6": "low",
    "email": "low",
}

_KIND_FOR_CLASS = {
    "url": FindingKind.STRING_HIT,
    "onion": FindingKind.STRING_HIT,
    "email": FindingKind.EMAIL,
    "ipv4": FindingKind.NETWORK_CONNECTION,
    "ipv6": FindingKind.NETWORK_CONNECTION,
    "registry_key": FindingKind.REGISTRY_KEY,
    "windows_path": FindingKind.FILE,
    "unix_path": FindingKind.FILE,
    "unc_path": FindingKind.FILE,
    "private_key": FindingKind.CREDENTIAL,
    "aws_key": FindingKind.CREDENTIAL,
    "jwt": FindingKind.CREDENTIAL,
    "powershell": FindingKind.EXECUTION_EVIDENCE,
}


class TriageNormalizer:
    tool = "triage"

    def normalize(
        self,
        output_dir: str | Path,
        *,
        job_id: str | None = None,
        artifact_sha256: str | None = None,
        tool_version: str = "1.0.0",
    ) -> list[Finding]:
        out = Path(output_dir)
        report = out / "triage.json"
        base = dict(
            tool=self.tool,
            tool_version=tool_version,
            feature="scan",
            job_id=job_id,
            artifact_sha256=artifact_sha256,
        )

        if not report.is_file():
            return [
                Finding(
                    **base,
                    kind=FindingKind.ERROR,
                    severity="medium",
                    title="triage produced no report",
                    data={"expected": str(report), "reason": "file not found"},
                )
            ]

        try:
            payload = json.loads(report.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
            return [
                Finding(
                    **base,
                    kind=FindingKind.ERROR,
                    severity="medium",
                    title="triage report is unreadable",
                    data={"error": f"{type(exc).__name__}: {exc}"},
                )
            ]

        findings: list[Finding] = []

        for label, entries in (payload.get("strings") or {}).items():
            kind = _KIND_FOR_CLASS.get(label, FindingKind.STRING_HIT)
            severity = _NOTABLE.get(label, "info")
            for entry in entries:
                findings.append(
                    Finding(
                        **base,
                        kind=kind,
                        severity=severity,
                        title=f"{label}: {entry.get('value', '')[:120]}",
                        source_offset=entry.get("offset"),
                        labels=["string", label],
                        data={
                            "class": label,
                            "value": entry.get("value"),
                            "encoding": entry.get("encoding"),
                        },
                    )
                )

        for carved in payload.get("carved") or []:
            findings.append(
                Finding(
                    **base,
                    kind=FindingKind.EMBEDDED_FILE,
                    severity="medium",
                    title=f"embedded {carved.get('type')} at offset {carved.get('offset')}",
                    source_offset=carved.get("offset"),
                    labels=["carved", str(carved.get("type"))],
                    data=carved,
                )
            )

        for flag in payload.get("flags") or []:
            findings.append(
                Finding(
                    **base,
                    kind=FindingKind.FLAG_CANDIDATE,
                    severity="high",
                    title=f"flag candidate: {flag.get('value')}",
                    source_offset=flag.get("offset"),
                    labels=["ctf", "flag"],
                    data=flag,
                )
            )

        entropy = payload.get("entropy") or {}
        if entropy:
            high_ratio = entropy.get("high_entropy_ratio", 0)
            findings.append(
                Finding(
                    **base,
                    kind=FindingKind.ARTIFACT_IDENTITY,
                    severity="medium" if high_ratio > 0.5 else "info",
                    title=(
                        f"entropy profile: mean {entropy.get('mean')} bits/byte, "
                        f"{entropy.get('high_entropy_regions', 0)} high-entropy blocks"
                    ),
                    labels=["entropy"],
                    data={
                        "mean": entropy.get("mean"),
                        "high_entropy_regions": entropy.get("high_entropy_regions"),
                        "high_entropy_ratio": high_ratio,
                        # The full point list can be thousands of entries; keep a
                        # sample so a UI can sparkline it without shipping it all.
                        "points_sample": (entropy.get("points") or [])[:128],
                        "points_total": len(entropy.get("points") or []),
                    },
                )
            )

        truncated = payload.get("truncated") or []
        if truncated:
            # Never let a cap look like a complete result.
            findings.append(
                Finding(
                    **base,
                    kind=FindingKind.ERROR,
                    severity="low",
                    title="triage output was capped",
                    labels=["truncated"],
                    data={"capped": truncated},
                )
            )

        return findings
