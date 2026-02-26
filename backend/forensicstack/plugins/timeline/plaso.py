import subprocess
import os
from typing import Dict, Any, Optional

class PlasoPlugin:
    """Plaso via Docker"""
    
    def __init__(self):
        self.name = "plaso"
        self.use_docker = True
        self.version = "20260119 (Docker)"
    
    def create_timeline(
        self,
        source: str,
        output_file: str,
        storage_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create timeline using Docker"""
        
        if not storage_file:
            storage_file = output_file.replace(".csv", ".plaso")
        
        # Convert Windows paths
        source_abs = os.path.abspath(source)
        output_abs = os.path.abspath(output_file)
        
        # Docker command
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{os.path.dirname(source_abs)}:/data",
            "log2timeline/plaso",
            "log2timeline.py",
            f"/data/{os.path.basename(storage_file)}",
            f"/data/{os.path.basename(source)}"
        ]
        
        print(f"Running Plaso via Docker...")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600
            )
            
            if result.returncode == 0:
                return {
                    "status": "success",
                    "method": "docker",
                    "storage_file": storage_file,
                    "output": result.stdout
                }
            else:
                return {
                    "status": "error",
                    "error": result.stderr
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}


def get_plaso_plugin() -> PlasoPlugin:
    return PlasoPlugin()
