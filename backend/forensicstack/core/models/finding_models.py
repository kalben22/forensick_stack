from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class Finding:
    tool: str
    artifact_type: str
    source: str
    timestamp: str | None
    data: Dict[str, Any]
    confidence: float