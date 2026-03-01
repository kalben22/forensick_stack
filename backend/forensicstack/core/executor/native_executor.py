"""
ForensicStack — NativeExecutor

Runs forensic tools directly as host processes instead of inside Docker.
Used for Windows-native tools (EZ Tools) when Docker adds no value because
the host is already Windows.

EZTOOLS_DIR env var (default C:\\EZTools) must point to the directory where
EZ Tools are installed.  Run scripts\\install-eztools.ps1 once to set this up.
"""

import os
import subprocess
import shutil
import uuid
from pathlib import Path

from forensicstack.core.plugin_registry import PLUGIN_REGISTRY

TMP_BASE = Path("tmp_jobs")

# ---------------------------------------------------------------------------
# EZ Tools: feature_id -> {exe (relative to EZTOOLS_DIR), CSV args builder}
# ---------------------------------------------------------------------------
_EZTOOLS_MAP = {
    "amcacheparser": {
        "exe": "AmcacheParser.exe",
        "args": lambda inp, out: ["-f", inp, "--csv", out, "--csvf", "amcache.csv"],
    },
    "appcompatcache": {
        "exe": "AppCompatCacheParser.exe",
        "args": lambda inp, out: ["-f", inp, "--csv", out, "--csvf", "appcompat.csv"],
    },
    "evtx": {
        "exe": r"EvtxECmd\EvtxECmd.exe",
        "args": lambda inp, out: ["-f", inp, "--csv", out, "--csvf", "evtx.csv"],
    },
    "jumplist": {
        "exe": "JLECmd.exe",
        "args": lambda inp, out: ["-f", inp, "--csv", out, "--csvf", "jumplist.csv"],
    },
    "lnk": {
        "exe": "LECmd.exe",
        "args": lambda inp, out: ["-f", inp, "--csv", out, "--csvf", "lnk.csv"],
    },
    "mft": {
        "exe": "MFTECmd.exe",
        "args": lambda inp, out: ["-f", inp, "--csv", out, "--csvf", "mft.csv"],
    },
    "prefetch": {
        "exe": "PECmd.exe",
        "args": lambda inp, out: ["-f", inp, "--csv", out, "--csvf", "prefetch.csv"],
    },
    "recyclebin": {
        "exe": "RBCmd.exe",
        "args": lambda inp, out: ["-f", inp, "--csv", out, "--csvf", "recyclebin.csv"],
    },
    "registry": {
        "exe": r"RECmd\RECmd.exe",
        "args": lambda inp, out: ["-f", inp, "--csv", out, "--csvf", "registry.csv"],
    },
    "shellbags": {
        "exe": "SBECmd.exe",
        "args": lambda inp, out: ["-f", inp, "--csv", out, "--csvf", "shellbags.csv"],
    },
    "sqlite": {
        "exe": r"SQLECmd\SQLECmd.exe",
        "args": lambda inp, out: ["-f", inp, "--csv", out, "--csvf", "sqlite.csv"],
    },
    "srum": {
        "exe": "SrumECmd.exe",
        "args": lambda inp, out: ["-f", inp, "--csv", out, "--csvf", "srum.csv"],
    },
    "bstrings": {
        "exe": "bstrings.exe",
        "args": lambda inp, out: ["-f", inp, "--csv", out, "--csvf", "bstrings.csv"],
    },
    "hasher": {
        "exe": "hasher.exe",
        "args": lambda inp, out: ["-f", inp, "--csv", out, "--csvf", "hasher.csv"],
    },
}

# Per-tool registries keyed by plugin name
_NATIVE_TOOL_MAPS = {
    "eztools": _EZTOOLS_MAP,
}

_DEFAULT_TOOL_DIRS = {
    "eztools": Path(r"C:\EZTools"),
}

_TOOL_DIR_ENV_VARS = {
    "eztools": "EZTOOLS_DIR",
}


def _resolve_exe(tool_name: str, relative_exe: str) -> Path:
    env_var = _TOOL_DIR_ENV_VARS.get(tool_name, "")
    tools_dir = Path(os.environ.get(env_var, str(_DEFAULT_TOOL_DIRS[tool_name])))

    direct = tools_dir / relative_exe
    if direct.exists():
        return direct

    # Fallback: search by filename (zip layout can vary by EZ Tools version)
    exe_name = Path(relative_exe).name
    for candidate in tools_dir.rglob(exe_name):
        return candidate

    env_hint = f"Set the {env_var} environment variable to point to your EZ Tools directory." if env_var else ""
    raise RuntimeError(
        f"Executable '{relative_exe}' not found under {tools_dir}. "
        f"Run scripts\\install-eztools.ps1 to install EZ Tools. {env_hint}".strip()
    )


class NativeExecutor:
    @staticmethod
    def run_plugin(
        tool_name: str,
        input_path: str,
        input_type: str | None = None,
        timeout: int | None = None,
    ) -> str:
        if tool_name not in PLUGIN_REGISTRY:
            raise ValueError(f"Unknown plugin: {tool_name}")
        plugin = PLUGIN_REGISTRY[tool_name]

        if tool_name not in _NATIVE_TOOL_MAPS:
            raise RuntimeError(f"No native tool map registered for '{tool_name}'")

        feature = input_type or plugin.get("default_type", "")
        tool_map = _NATIVE_TOOL_MAPS[tool_name]

        if not feature or feature not in tool_map:
            raise RuntimeError(
                f"Unknown feature '{feature}' for native tool '{tool_name}'. "
                f"Available: {', '.join(tool_map)}"
            )

        # Set up isolated job directories
        job_id = str(uuid.uuid4())
        job_dir = TMP_BASE / job_id
        job_in  = job_dir / "input"
        job_out = job_dir / "output"
        job_in.mkdir(parents=True, exist_ok=True)
        job_out.mkdir(parents=True, exist_ok=True)

        src = Path(input_path)
        if src.is_dir():
            shutil.copytree(src, job_in, dirs_exist_ok=True)
        else:
            shutil.copy2(src, job_in)

        # Find the (first) file in the copied input dir
        input_files = [p for p in job_in.rglob("*") if p.is_file()]
        if not input_files:
            raise RuntimeError("No input file found in job input directory")
        input_file = input_files[0]

        cfg      = tool_map[feature]
        exe_path = _resolve_exe(tool_name, cfg["exe"])
        args     = cfg["args"](str(input_file), str(job_out))
        cmd      = [str(exe_path)] + args

        print(f"[native] Running: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                check=False,
                text=True,
                capture_output=True,
                timeout=timeout or plugin.get("timeout", 600),
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"Native tool timed out after {exc.timeout}s") from exc

        if result.stdout:
            print(result.stdout, end="")
        if result.returncode != 0 and result.stderr:
            print(result.stderr, end="")

        return str(job_out)
