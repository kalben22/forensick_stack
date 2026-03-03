import json
from pathlib import Path
from forensicstack.core.models.finding_models import Finding
from forensicstack.core.normalizers.base_normalizer import BaseNormalizer


class VolatilityNormalizer(BaseNormalizer):

    # Internal metadata keys added by Volatility3 that are not result data.
    _STRIP_KEYS = {"__children"}

    def normalize(self, output_dir: str):
        findings = []
        any_valid_json = False  # tracks whether vol3 produced parseable output at all

        for json_file in Path(output_dir).glob("*.json"):
            raw = json_file.read_text(encoding="utf-8").strip()
            if not raw:
                continue

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            any_valid_json = True

            # ── Flat-array format (Volatility3 v2+ default JSON renderer) ────
            # vol3 --renderer json emits a plain list of dicts, one per row.
            # Example: [{"PID": 4, "ImageFileName": "System", "__children": []}, ...]
            if isinstance(data, list):
                for row in data:
                    if row is None:
                        continue
                    row_dict = (
                        {k: v for k, v in row.items() if k not in self._STRIP_KEYS}
                        if isinstance(row, dict)
                        else {"value": row}
                    )
                    findings.append(
                        Finding(
                            tool="volatility",
                            artifact_type=json_file.stem,
                            source="memory",
                            timestamp=None,
                            data=row_dict,
                            confidence=0.7,
                        )
                    )
                continue  # done with this file

            # ── Legacy TreeGrid formats ───────────────────────────────────────
            # v1.x  {"columns": [...], "rows": [...]}
            # v2.x  {"treegrid": {"columns": [...], "rows": [...]}}
            # v2.5+ {"type": "TreeGrid", "version": 1, "columns": [...], "rows": [...]}
            if isinstance(data, dict):
                if "treegrid" in data:
                    data = data["treegrid"]
                # else: columns / rows already at top level (type == "TreeGrid" or v1.x)

            raw_columns = data.get("columns", [])
            rows = data.get("rows", []) or []

            # columns can be plain strings or dicts {"name": "PID", "type": "int"}
            column_names = [
                c["name"] if isinstance(c, dict) else c
                for c in raw_columns
            ]

            for row in rows:
                if row is None:
                    continue
                if isinstance(row, list) and column_names:
                    row_dict = dict(zip(column_names, row))
                elif isinstance(row, dict):
                    row_dict = {k: v for k, v in row.items() if k not in self._STRIP_KEYS}
                else:
                    row_dict = {"value": row}

                findings.append(
                    Finding(
                        tool="volatility",
                        artifact_type=json_file.stem,
                        source="memory",
                        timestamp=None,
                        data=row_dict,
                        confidence=0.7,
                    )
                )

        # Surface .log content as an error finding ONLY when vol3 produced no
        # parseable JSON output (container crashed, missing symbols, wrong format,
        # etc.).  If vol3 ran cleanly but found 0 rows we do NOT surface the log
        # because Volatility3 always writes progress messages to stderr that would
        # be misleadingly shown as errors.
        if not any_valid_json:
            for log_file in Path(output_dir).glob("*.log"):
                content = log_file.read_text(encoding="utf-8", errors="replace").strip()
                if content:
                    findings.append(
                        Finding(
                            tool="volatility",
                            artifact_type="_error",
                            source="memory",
                            timestamp=None,
                            data={"message": content},
                            confidence=0.0,
                        )
                    )

        return findings
