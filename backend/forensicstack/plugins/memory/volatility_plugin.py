import subprocess
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import tempfile


class VolatilityPlugin:
    """Volatility 3 integration - utilise Volatility normalement"""
    
    def __init__(self, volatility_path: str = "vol.py"):
        """
        Initialize Volatility plugin
        
        Args:
            volatility_path: Path to vol.py (default: "vol.py" si dans PATH)
        """
        self.volatility_path = volatility_path
        self.name = "volatility3"
        self.version = self._get_version()
    
    def _get_version(self) -> str:
        """Get Volatility version"""
        try:
            result = subprocess.run(
                ["python", "-m", "volatility3", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip()
        except:
            return "unknown"
    
    def list_plugins(self) -> List[str]:
        """List all available Volatility plugins"""
        try:
            result = subprocess.run(
                ["python", "-m", "volatility3", "--help"],
                capture_output=True,
                text=True,
                timeout=10
            )
            # Parser la sortie pour extraire les plugins
            plugins = []
            lines = result.stdout.split('\n')
            in_plugins = False
            for line in lines:
                if 'windows.' in line or 'linux.' in line or 'mac.' in line:
                    plugin = line.strip().split()[0]
                    plugins.append(plugin)
            return plugins
        except Exception as e:
            print(f"Error listing plugins: {e}")
            return []
    
    def run(
        self,
        dump_path: str,
        plugin: str,
        output_format: str = "text",
        output_file: Optional[str] = None,
        extra_args: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Execute a Volatility plugin - EXACTEMENT comme en ligne de commande
        
        Args:
            dump_path: Path to memory dump
            plugin: Plugin name (e.g., "windows.pslist", "windows.netscan")
            output_format: Output format ("text", "json", "csv", "html")
            output_file: Optional output file path
            extra_args: Additional arguments (e.g., ["--pid", "1234"])
        
        Returns:
            Dict with status and results
        
        Example:
            vol = VolatilityPlugin()
            result = vol.run(
                "memory.dmp",
                "windows.pslist",
                output_format="json"
            )
        """
        # Construire la commande exactement comme Volatility
        cmd = [
            "python", "-m", "volatility3",
            "-f", dump_path,
            plugin
        ]
        
        # Ajouter le format de sortie
        if output_format != "text":
            cmd.extend(["-r", output_format])
        
        # Ajouter le fichier de sortie si spécifié
        if output_file:
            cmd.extend(["-o", output_file])
        
        # Ajouter les arguments supplémentaires
        if extra_args:
            cmd.extend(extra_args)
        
        print(f"🔬 Running: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes max
            )
            
            if result.returncode == 0:
                return {
                    "status": "success",
                    "plugin": plugin,
                    "output": result.stdout,
                    "command": ' '.join(cmd),
                    "output_file": output_file
                }
            else:
                return {
                    "status": "error",
                    "plugin": plugin,
                    "error": result.stderr,
                    "command": ' '.join(cmd)
                }
        
        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "plugin": plugin,
                "error": "Timeout (10 minutes exceeded)",
                "command": ' '.join(cmd)
            }
        except Exception as e:
            return {
                "status": "error",
                "plugin": plugin,
                "error": str(e),
                "command": ' '.join(cmd)
            }
    
    # Raccourcis pour plugins courants Windows
    def pslist(self, dump_path: str) -> Dict[str, Any]:
        """List processes"""
        return self.run(dump_path, "windows.pslist")
    
    def pstree(self, dump_path: str) -> Dict[str, Any]:
        """Process tree"""
        return self.run(dump_path, "windows.pstree")
    
    def psscan(self, dump_path: str) -> Dict[str, Any]:
        """Scan for processes"""
        return self.run(dump_path, "windows.psscan")
    
    def netscan(self, dump_path: str) -> Dict[str, Any]:
        """Scan network connections"""
        return self.run(dump_path, "windows.netscan")
    
    def netstat(self, dump_path: str) -> Dict[str, Any]:
        """Network statistics"""
        return self.run(dump_path, "windows.netstat")
    
    def malfind(self, dump_path: str) -> Dict[str, Any]:
        """Find malicious code"""
        return self.run(dump_path, "windows.malfind")
    
    def dlllist(self, dump_path: str, pid: Optional[int] = None) -> Dict[str, Any]:
        """List DLLs"""
        extra_args = ["--pid", str(pid)] if pid else None
        return self.run(dump_path, "windows.dlllist", extra_args=extra_args)
    
    def handles(self, dump_path: str, pid: Optional[int] = None) -> Dict[str, Any]:
        """List handles"""
        extra_args = ["--pid", str(pid)] if pid else None
        return self.run(dump_path, "windows.handles", extra_args=extra_args)
    
    def cmdline(self, dump_path: str) -> Dict[str, Any]:
        """Process command lines"""
        return self.run(dump_path, "windows.cmdline")
    
    def filescan(self, dump_path: str) -> Dict[str, Any]:
        """Scan for file objects"""
        return self.run(dump_path, "windows.filescan")
    
    def registry_hivelist(self, dump_path: str) -> Dict[str, Any]:
        """List registry hives"""
        return self.run(dump_path, "windows.registry.hivelist")
    
    def registry_printkey(self, dump_path: str, key: str) -> Dict[str, Any]:
        """Print registry key"""
        return self.run(dump_path, "windows.registry.printkey", extra_args=["--key", key])


# Helper function
def get_volatility_plugin() -> VolatilityPlugin:
    """Get a Volatility plugin instance"""
    return VolatilityPlugin()
