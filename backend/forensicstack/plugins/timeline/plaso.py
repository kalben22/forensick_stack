"""
Plaso (log2timeline) plugin — forensic super-timeline generation via subprocess.

Requires Plaso to be installed and available in PATH:
  - log2timeline.py  (timeline extraction)
  - psort.py         (sorting & filtering)
  - pinfo.py         (storage info)

Install: pip install plaso  OR  docker run log2timeline/plaso
"""
import subprocess
import shutil
import os
import tempfile
from typing import Dict, Any, List, Optional


class PlasoPlugin:
    """Plaso / log2timeline integration for super-timeline generation."""

    def __init__(self):
        self.name = "plaso"
        self.log2timeline = self._find_command("log2timeline.py") or self._find_command("log2timeline")
        self.psort = self._find_command("psort.py") or self._find_command("psort")
        self.pinfo = self._find_command("pinfo.py") or self._find_command("pinfo")
        self._check_tools()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_command(self, name: str) -> Optional[str]:
        return shutil.which(name)

    def _check_tools(self):
        if not self.log2timeline:
            print("[Plaso] WARNING: 'log2timeline' not found in PATH")
        if not self.psort:
            print("[Plaso] WARNING: 'psort' not found in PATH")

    def _run(self, cmd: List[str], timeout: int = 3600) -> Dict[str, Any]:
        """Run a shell command and return structured result."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if result.returncode == 0:
                return {"status": "success", "output": result.stdout, "stderr": result.stderr}
            return {
                "status": "error",
                "error": result.stderr or f"Exit code {result.returncode}",
                "stdout": result.stdout,
            }
        except FileNotFoundError as e:
            return {"status": "error", "error": f"Tool not found: {e}"}
        except subprocess.TimeoutExpired:
            return {"status": "error", "error": f"Timeout after {timeout}s"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_timeline(self, source_path: str, output_file: str) -> Dict[str, Any]:
        """
        Full pipeline: log2timeline → plaso storage → psort → CSV timeline.

        Args:
            source_path:  Path to source (disk image, directory, or memory dump)
            output_file:  Destination path for the output CSV timeline

        Returns:
            Dict with status and path to the generated timeline
        """
        if not self.log2timeline:
            return {"status": "error", "error": "log2timeline not installed"}

        print(f"[Plaso] Creating timeline for: {source_path}")

        # Step 1: log2timeline → .plaso storage file
        plaso_storage = output_file.replace(".csv", ".plaso")
        if not plaso_storage.endswith(".plaso"):
            plaso_storage += ".plaso"

        l2t_result = self._run_log2timeline(source_path, plaso_storage)
        if l2t_result["status"] != "success":
            return l2t_result

        # Step 2: psort → CSV
        if self.psort:
            sort_result = self._run_psort(plaso_storage, output_file)
            if sort_result["status"] != "success":
                return sort_result
            return {
                "status": "success",
                "source": source_path,
                "plaso_storage": plaso_storage,
                "timeline_csv": output_file,
                "message": "Timeline generated successfully",
            }

        # psort not available — return the raw storage file
        return {
            "status": "success",
            "source": source_path,
            "plaso_storage": plaso_storage,
            "message": "Storage file created (psort not available for CSV export)",
        }

    def extract_events(self, plaso_storage: str, output_file: str,
                       time_slice: Optional[str] = None,
                       query: Optional[str] = None) -> Dict[str, Any]:
        """
        Run psort on an existing .plaso storage to produce a filtered CSV.

        Args:
            plaso_storage: Path to .plaso file
            output_file:   Destination CSV path
            time_slice:    Optional time range, e.g. "2024-01-01T00:00:00,2024-12-31T23:59:59"
            query:         Optional psort filter query
        """
        if not self.psort:
            return {"status": "error", "error": "psort not installed"}

        return self._run_psort(plaso_storage, output_file, time_slice=time_slice, query=query)

    def get_storage_info(self, plaso_storage: str) -> Dict[str, Any]:
        """Get metadata about an existing .plaso storage file using pinfo."""
        if not self.pinfo:
            return {"status": "error", "error": "pinfo not installed"}

        result = self._run([self.pinfo, plaso_storage], timeout=60)
        return result

    # ------------------------------------------------------------------
    # Sub-command runners
    # ------------------------------------------------------------------

    def _run_log2timeline(self, source_path: str, plaso_storage: str) -> Dict[str, Any]:
        """Run log2timeline to extract events into a .plaso storage file."""
        cmd = [
            self.log2timeline,
            "--storage-file", plaso_storage,
            "--parsers", "all",
            source_path,
        ]
        print(f"[Plaso] Running: {' '.join(cmd)}")
        return self._run(cmd, timeout=7200)  # 2h max for large images

    def _run_psort(self, plaso_storage: str, output_file: str,
                   time_slice: Optional[str] = None,
                   query: Optional[str] = None) -> Dict[str, Any]:
        """Run psort to convert .plaso storage to CSV."""
        cmd = [
            self.psort,
            "-o", "l2tcsv",
            "-w", output_file,
            plaso_storage,
        ]
        if time_slice:
            cmd.extend(["--slice", time_slice])
        if query:
            cmd.append(query)

        print(f"[Plaso] Running: {' '.join(cmd)}")
        return self._run(cmd, timeout=3600)


def get_plaso_plugin() -> PlasoPlugin:
    return PlasoPlugin()
