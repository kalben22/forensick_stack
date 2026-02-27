import csv
from pathlib import Path
from forensicstack.core.models.finding_models import Finding
from forensicstack.core.normalizers.base_normalizer import BaseNormalizer


class ILEAPPNormalizer(BaseNormalizer):

    def normalize(self, output_dir: str):

        findings = []

        reports_path = Path(output_dir) / "Reports"

        if not reports_path.exists():
            return findings

        for csv_file in reports_path.glob("*.csv"):

            artifact_type = csv_file.stem

            with open(csv_file, newline="", encoding="utf-8", errors="ignore") as f:
                reader = csv.DictReader(f)

                for row in reader:
                    findings.append(
                        Finding(
                            tool="ileapp",
                            artifact_type=artifact_type,
                            source=artifact_type,
                            timestamp=row.get("Date") or row.get("Timestamp"),
                            data=row,
                            confidence=0.6
                        )
                    )

        return findings