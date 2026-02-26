import yara
from typing import Dict, Any, List
from pathlib import Path


class YaraPlugin:
    """YARA pattern matching"""
    
    def __init__(self):
        self.name = "yara"
        self.version = yara.__version__
    
    def scan_file(self, file_path: str, rules_path: str) -> Dict[str, Any]:
        """Scan a file with YARA rules"""
        try:
            rules = yara.compile(filepath=rules_path)
            matches = rules.match(file_path)
            
            return {
                "status": "success",
                "file": file_path,
                "matches": [
                    {
                        "rule": m.rule,
                        "namespace": m.namespace,
                        "tags": list(m.tags),
                        "meta": dict(m.meta),
                        "strings": [(s.identifier, s.instances[0].matched_data if s.instances else b"") for s in m.strings]
                    }
                    for m in matches
                ],
                "total_matches": len(matches)
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def scan_directory(self, directory: str, rules_path: str) -> Dict[str, Any]:
        """Scan all files in directory"""
        results = []
        
        for file_path in Path(directory).rglob("*"):
            if file_path.is_file():
                result = self.scan_file(str(file_path), rules_path)
                if result.get("matches"):
                    results.append(result)
        
        return {
            "status": "success",
            "directory": directory,
            "scanned_files": len(list(Path(directory).rglob("*"))),
            "matches": results,
            "total_detections": len(results)
        }


def get_yara_plugin() -> YaraPlugin:
    return YaraPlugin()
