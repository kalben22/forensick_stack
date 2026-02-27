import json
from pathlib import Path
from forensicstack.core.models.finding_models import Finding
from forensicstack.core.normalizers.base_normalizer import BaseNormalizer


class VolatilityNormalizer(BaseNormalizer):

    def normalize(self, output_dir: str):

        findings = []

        for json_file in Path(output_dir).glob("*.json"):

            plugin_name = json_file.stem

            data = json.loads(json_file.read_text(encoding="utf-8"))

            rows = data.get("rows", [])

            for row in rows:
                findings.append(
                    Finding(
                        tool="volatility",
                        artifact_type=plugin_name,
                        source="memory",
                        timestamp=None,
                        data=row,
                        confidence=0.7
                    )
                )

        return findings