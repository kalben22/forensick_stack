from pathlib import Path
from typing import List, Dict
import os

RULES_DIR = Path(__file__).parent / "rules" / "yara"

class YaraRulesManager:
    """Manage YARA rules collections"""
    
    def __init__(self):
        self.rules_dir = RULES_DIR
    
    def list_collections(self) -> List[str]:
        """List available rule collections"""
        if not self.rules_dir.exists():
            return []
        return [d.name for d in self.rules_dir.iterdir() if d.is_dir()]
    
    def get_rule_files(self, collection: str = "community") -> List[Path]:
        """Get all .yar files in a collection"""
        collection_path = self.rules_dir / collection
        if not collection_path.exists():
            return []
        return list(collection_path.rglob("*.yar")) + list(collection_path.rglob("*.yara"))
    
    def get_malware_rules(self) -> Path:
        """Get path to malware rules"""
        return self.rules_dir / "community" / "malware"
    
    def get_apt_rules(self) -> Path:
        """Get APT-related rules"""
        return self.rules_dir / "community" / "apt"
    
    def get_webshell_rules(self) -> Path:
        """Get webshell rules"""
        return self.rules_dir / "community" / "webshells"


def get_rules_manager():
    return YaraRulesManager()
