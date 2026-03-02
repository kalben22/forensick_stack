import json
from pathlib import Path
from forensicstack.core.models.finding_models import Finding
from forensicstack.core.normalizers.base_normalizer import BaseNormalizer


class VolatilityNormalizer(BaseNormalizer):

    def normalize(self, output_dir: str):
        findings = []

        for json_file in Path(output_dir).glob("*.json"):
            raw = json_file.read_text(encoding="utf-8").strip()
            if not raw:
                continue

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            # Normalise the various JSON shapes Volatility3 emits across versions:
            #
            #   v1.x  {"columns": [...], "rows": [...]}
            #   v2.x  {"treegrid": {"columns": [...], "rows": [...]}}
            #   v2.5+ {"type": "TreeGrid", "version": 1,
            #          "columns": [...], "rows": [...]}
            if isinstance(data, dict):
                if "treegrid" in data:
                    data = data["treegrid"]
                elif data.get("type") == "TreeGrid":
                    pass  # columns / rows are already at the top level

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
                    row_dict = row
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

        # If no findings were produced, surface .log content as an error finding
        # so the UI shows the actual Volatility3 error (missing symbols, wrong
        # image format, unsupported plugin, etc.).
        if not findings:
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
