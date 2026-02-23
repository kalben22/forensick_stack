import subprocess
from pathlib import Path

class VolatilityPlugin:
    def __init__(self):
        self.name = "volatility"
        self.version = "3.0"
    
    def run_plugin(self, dump_path: str, plugin: str):
        """Run Volatility plugin"""
        cmd = [
            "volatility3",
            "-f", dump_path,
            plugin
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            return {
                "status": "success",
                "output": result.stdout,
                "error": result.stderr
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def pslist(self, dump_path: str):
        """List processes"""
        return self.run_plugin(dump_path, "windows.pslist")