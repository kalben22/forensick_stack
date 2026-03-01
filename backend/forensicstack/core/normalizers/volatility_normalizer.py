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

            # Volatility 3 --renderer json outputs:
            #   {"columns": [...], "rows": [[...], ...]}
            # Some versions wrap it: {"treegrid": {"columns": ..., "rows": ...}}
            if "treegrid" in data:
                data = data["treegrid"]

            raw_columns = data.get("columns", [])
            rows = data.get("rows", [])

            # columns can be strings or dicts {"name": "PID", "type": "int"}
            column_names = [
                c["name"] if isinstance(c, dict) else c
                for c in raw_columns
            ]

            for row in rows:
                if isinstance(row, list) and column_names:
                    # Zip column names with values → readable labeled dict
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

        return findings
