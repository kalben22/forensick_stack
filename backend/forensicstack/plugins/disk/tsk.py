"""
The Sleuth Kit (TSK) plugin — disk image analysis via subprocess.

Requires TSK tools to be installed and available in PATH:
  - mmls   (partition layout)
  - fls    (file listing)
  - mactime (timeline)
  - istat  (inode info)
"""
import subprocess
import shutil
from typing import Dict, Any, List, Optional


class TSKPlugin:
    """The Sleuth Kit integration for disk image analysis."""

    def __init__(self):
        self.name = "tsk"
        self._check_tools()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _check_tools(self):
        """Warn if TSK tools are not found in PATH."""
        for tool in ("mmls", "fls", "mactime"):
            if not shutil.which(tool):
                print(f"[TSK] WARNING: '{tool}' not found in PATH")

    def _run(self, cmd: List[str], timeout: int = 120) -> Dict[str, Any]:
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

    def list_partitions(self, image_path: str) -> Dict[str, Any]:
        """
        List partition table of a disk image using mmls.

        Returns partition offsets, sizes and types.
        """
        print(f"[TSK] Listing partitions: {image_path}")
        result = self._run(["mmls", image_path])

        if result["status"] == "success":
            partitions = self._parse_mmls(result["output"])
            result["partitions"] = partitions
            result["total"] = len(partitions)

        return result

    def list_files(
        self,
        image_path: str,
        partition_offset: int = 0,
        recursive: bool = True,
    ) -> Dict[str, Any]:
        """
        List files in a partition using fls.

        Args:
            image_path:        Path to disk image
            partition_offset:  Sector offset of the partition (from mmls)
            recursive:         Whether to recurse into directories
        """
        print(f"[TSK] Listing files at offset {partition_offset}: {image_path}")
        cmd = ["fls", "-o", str(partition_offset)]
        if recursive:
            cmd.append("-r")
        cmd.append(image_path)

        result = self._run(cmd, timeout=300)

        if result["status"] == "success":
            files = self._parse_fls(result["output"])
            result["files"] = files
            result["total"] = len(files)

        return result

    def generate_timeline(self, image_path: str, partition_offset: int = 0) -> Dict[str, Any]:
        """
        Generate a filesystem timeline using fls + mactime.

        Produces MAC (Modified/Accessed/Changed) timestamps for all files.
        """
        print(f"[TSK] Generating timeline for: {image_path}")

        # Step 1: fls -m to get body file format
        fls_result = self._run(
            ["fls", "-o", str(partition_offset), "-m", "/", "-r", image_path],
            timeout=300,
        )
        if fls_result["status"] != "success":
            return fls_result

        # Step 2: pipe body file into mactime
        try:
            mactime = subprocess.run(
                ["mactime", "-b", "-"],
                input=fls_result["output"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            timeline_output = mactime.stdout
        except Exception as e:
            timeline_output = fls_result["output"]  # fallback: raw body file

        events = self._parse_timeline(timeline_output)
        return {
            "status": "success",
            "image": image_path,
            "partition_offset": partition_offset,
            "events": events,
            "total": len(events),
        }

    # ------------------------------------------------------------------
    # Output parsers
    # ------------------------------------------------------------------

    def _parse_mmls(self, output: str) -> List[Dict[str, Any]]:
        """Parse mmls output into list of partition dicts."""
        partitions = []
        for line in output.splitlines():
            line = line.strip()
            # mmls lines look like: "000:  Meta         0000000000   0000000000   0000000001   Primary Table (#0)"
            if not line or line.startswith("DOS") or line.startswith("Units"):
                continue
            parts = line.split(None, 5)
            if len(parts) >= 5 and parts[0].rstrip(":").isdigit():
                partitions.append({
                    "slot": parts[0].rstrip(":"),
                    "type": parts[1],
                    "start": int(parts[2]),
                    "end": int(parts[3]),
                    "length": int(parts[4]),
                    "description": parts[5] if len(parts) > 5 else "",
                })
        return partitions

    def _parse_fls(self, output: str) -> List[Dict[str, Any]]:
        """Parse fls output into list of file dicts."""
        files = []
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            # fls lines look like: "r/r 5:   filename.txt"
            parts = line.split(None, 2)
            if len(parts) >= 3:
                files.append({
                    "type": parts[0],
                    "inode": parts[1].rstrip(":"),
                    "name": parts[2],
                })
        return files

    def _parse_timeline(self, output: str) -> List[Dict[str, Any]]:
        """Parse mactime output into list of event dicts."""
        events = []
        for line in output.splitlines():
            line = line.strip()
            if not line or line.startswith("Date"):
                continue
            parts = line.split(",", 9)
            if len(parts) >= 8:
                events.append({
                    "date": parts[0],
                    "size": parts[1],
                    "type": parts[2],
                    "mode": parts[3],
                    "uid": parts[4],
                    "gid": parts[5],
                    "meta": parts[6],
                    "file": parts[7] if len(parts) > 7 else "",
                })
        return events


def get_tsk_plugin() -> TSKPlugin:
    return TSKPlugin()
