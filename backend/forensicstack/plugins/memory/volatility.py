import subprocess
import re
from typing import Dict, Any, List, Optional
import shutil

class VolatilityPlugin:
    """Volatility 3 integration"""
    
    def __init__(self):
        self.name = "volatility3"
        self.vol_command = self._find_volatility_command()
        self.version = self._get_version()
    
    def _find_volatility_command(self) -> List[str]:
        """Find the correct Volatility command"""
        # Try different commands
        commands = [
            ["vol"],
            ["vol.py"],
            ["volatility3"],
            ["python", "-m", "volatility3.cli"]
        ]
        
        for cmd in commands:
            try:
                result = subprocess.run(
                    cmd + ["-h"],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    print(f"Found Volatility: {' '.join(cmd)}")
                    return cmd
            except:
                continue
        
        print("Volatility not found, using default: vol")
        return ["vol"]
    
    def _get_version(self) -> str:
        try:
            result = subprocess.run(
                self.vol_command + ["--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip() or "3.0+"
        except:
            return "3.0+"
    
    def list_plugins(self) -> List[str]:
        """List ALL available Volatility plugins"""
        try:
            result = subprocess.run(
                self.vol_command + ["-h"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            plugins = []
            lines = result.stdout.split('\n')
            
            # Parser tous les plugins
            in_plugins_section = False
            for line in lines:
                # Détecter la section des plugins
                if 'windows.' in line or 'linux.' in line or 'mac.' in line:
                    in_plugins_section = True
                
                if in_plugins_section:
                    # Extraire les noms de plugins
                    match = re.search(r'(windows\.|linux\.|mac\.)[a-z._]+', line)
                    if match:
                        plugin_name = match.group(0)
                        plugins.append(plugin_name)
            
            # Si le parsing échoue, retourner une liste complète connue
            if len(plugins) < 20:
                plugins = self._get_default_plugins()
            
            return sorted(set(plugins))
        
        except Exception as e:
            print(f"Error listing plugins: {e}")
            return self._get_default_plugins()
    
    def _get_default_plugins(self) -> List[str]:
        """Return a comprehensive list of known Volatility3 plugins"""
        return [
            # Windows - Process Analysis
            "windows.pslist", "windows.pstree", "windows.psscan",
            "windows.dlllist", "windows.handles", "windows.cmdline",
            "windows.envars", "windows.privileges", "windows.getsids",
            
            # Windows - Network
            "windows.netscan", "windows.netstat",
            
            # Windows - Registry
            "windows.registry.hivelist", "windows.registry.printkey",
            "windows.registry.userassist", "windows.registry.certificates",
            
            # Windows - Files
            "windows.filescan", "windows.dumpfiles",
            
            # Windows - Malware
            "windows.malfind", "windows.ldrmodules", "windows.modscan",
            "windows.driverscan", "windows.ssdt", "windows.callbacks",
            "windows.devicetree",
            
            # Windows - Memory
            "windows.memmap", "windows.virtmap", "windows.vadinfo",
            "windows.vadyarascan",
            
            # Windows - Misc
            "windows.info", "windows.modules", "windows.symlinkscan",
            "windows.mbrscan", "windows.mftscan",
            
            # Linux
            "linux.pslist", "linux.pstree", "linux.bash",
            "linux.check_afinfo", "linux.check_creds", "linux.check_idt",
            "linux.check_modules", "linux.check_syscall",
            "linux.elfs", "linux.keyboard_notifiers", "linux.lsmod",
            "linux.lsof", "linux.malfind", "linux.proc", "linux.sockstat",
            "linux.tty_check",
            
            # macOS
            "mac.pslist", "mac.pstree", "mac.lsmod", "mac.netstat",
            "mac.ifconfig", "mac.list_files", "mac.bash",
            "mac.check_syscalls", "mac.check_sysctl", "mac.check_trap_table",
            "mac.kevents", "mac.proc_maps", "mac.tasks", "mac.timers"
        ]
    
    def run(
        self,
        dump_path: str,
        plugin: str,
        output_format: str = "text",
        output_file: Optional[str] = None,
        extra_args: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Execute Volatility plugin"""
        cmd = self.vol_command + ["-f", dump_path, plugin]
        
        if output_format != "text":
            cmd.extend(["-r", output_format])
        
        if output_file:
            cmd.extend(["-o", output_file])
        
        if extra_args:
            cmd.extend(extra_args)
        
        print(f"Running: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode == 0:
                return {
                    "status": "success",
                    "plugin": plugin,
                    "output": result.stdout,
                    "command": ' '.join(cmd)
                }
            else:
                return {
                    "status": "error",
                    "plugin": plugin,
                    "error": result.stderr,
                    "stderr": result.stderr,
                    "stdout": result.stdout,
                    "command": ' '.join(cmd)
                }
        except subprocess.TimeoutExpired:
            return {"status": "error", "plugin": plugin, "error": "Timeout (10 minutes)"}
        except Exception as e:
            return {"status": "error", "plugin": plugin, "error": str(e)}
    
    # Raccourcis
    def pslist(self, dump_path: str):
        return self.run(dump_path, "windows.pslist")
    
    def netscan(self, dump_path: str):
        return self.run(dump_path, "windows.netscan")
    
    def malfind(self, dump_path: str):
        return self.run(dump_path, "windows.malfind")


def get_volatility_plugin() -> VolatilityPlugin:
    return VolatilityPlugin()
