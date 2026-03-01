import csv
from pathlib import Path
from forensicstack.core.models.finding_models import Finding
from forensicstack.core.normalizers.base_normalizer import BaseNormalizer


class EZToolsNormalizer(BaseNormalizer):
    """
    Normalizer for Eric Zimmerman's EZ Tools.

    EZ Tools write CSV output files — each row becomes a Finding.
    The CSV stem (e.g. "evtx", "mft", "prefetch") is used as artifact_type.
    utf-8-sig encoding handles the BOM that .NET CSV writers often emit.
    """

    def normalize(self, output_dir: str):
        findings = []
        out_path = Path(output_dir)

        for csv_file in out_path.glob("*.csv"):
            try:
                with csv_file.open(encoding="utf-8-sig", newline="") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        findings.append(
                            Finding(
                                tool="eztools",
                                artifact_type=csv_file.stem,
                                source="filesystem",
                                timestamp=None,
                                data=dict(row),
                                confidence=0.85,
                            )
                        )
            except Exception:
                continue

        # Surface stderr/log output as an error finding when no CSV produced
        if not findings:
            for log_file in out_path.glob("*.log"):
                content = log_file.read_text(encoding="utf-8", errors="replace").strip()
                if content:
                    findings.append(
                        Finding(
                            tool="eztools",
                            artifact_type="_error",
                            source="filesystem",
                            timestamp=None,
                            data={"message": content},
                            confidence=0.0,
                        )
                    )

        return findings
