import json
from pathlib import Path
from forensicstack.core.models.finding_models import Finding
from forensicstack.core.normalizers.base_normalizer import BaseNormalizer


class ExiftoolNormalizer(BaseNormalizer):

    def normalize(self, output_dir: str):

        findings = []

        for file in Path(output_dir).glob("*_raw.json"):

            data = json.loads(file.read_text(encoding="utf-8"))

            for item in data:

                findings.append(
                    Finding(
                        tool="exiftool",
                        artifact_type="file_metadata",
                        source=item.get("SourceFile"),
                        timestamp=item.get("DateTimeOriginal"),
                        data=item,
                        confidence=0.4
                    )
                )

        return findings