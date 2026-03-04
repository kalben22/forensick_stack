import subprocess, uuid, os
from pathlib import Path
from forensicstack.core.plugin_registry import PLUGIN_REGISTRY

# Anchor to the backend package root â€” works both in Docker (/app) and on
# the Windows host, regardless of process working directory.
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent.parent
TMP_BASE = _BACKEND_DIR / "tmp_jobs"

# â”€â”€ Execution mode detection â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#
# Two modes are supported:
#
#   DooD (Docker-outside-Docker)
#     The worker itself runs inside a Docker container and spawns child
#     containers via the host Docker socket.  In this mode, host-path
#     translation is fragile (especially on Windows) because docker-compose
#     evaluates ${PWD} differently depending on how / where it is invoked.
#
#     Fix: use --volumes-from <worker-container> so the forensic tool container
#     inherits the worker's filesystem mounts.  The worker already has the
#     backend directory mapped at /app, so the child sees the same paths with
#     no translation required.
#
#   Native
#     The worker runs directly on the host (no Docker wrapping).  Bind mounts
#     use local filesystem paths that Docker Desktop resolves correctly on both
#     Linux and Windows.  HOST_BACKEND_DIR is not required.
#
# Set WORKER_CONTAINER_NAME to the value of `container_name` in docker-compose
# (default: fs_worker).  The docker-compose.yml injects this automatically.

_WORKER_CONTAINER = os.getenv("WORKER_CONTAINER_NAME", "").strip() or None


def _is_dood() -> bool:
    """True when the worker process is itself running inside a Docker container."""
    return _WORKER_CONTAINER is not None or Path("/.dockerenv").exists()


# Kept for native-mode fallback â€” only used when _is_dood() is False.
_HOST_BACKEND_DIR = os.getenv("HOST_BACKEND_DIR", "").strip() or None


def _host_path(container_path: Path) -> str:
    """
    Translate a container-internal path to the equivalent host path.
    Only called in native mode (not DooD).
    """
    if _HOST_BACKEND_DIR:
        try:
            rel = container_path.relative_to(_BACKEND_DIR)
            return str(Path(_HOST_BACKEND_DIR) / rel)
        except ValueError:
            pass
    return str(container_path)


class DockerExecutor:
    @staticmethod
    def run_plugin(tool_name: str, input_path: str, input_type: str|None = None, timeout: int|None = None):
        if tool_name not in PLUGIN_REGISTRY:
            raise ValueError("Unknown plugin: "+tool_name)
        plugin = PLUGIN_REGISTRY[tool_name]

        job_id = str(uuid.uuid4())
        job_dir = TMP_BASE / job_id
        job_out = job_dir / "output"
        job_out.mkdir(parents=True, exist_ok=True)

        # For files: mount the parent directory so the file appears as /data/<name>.
        # For directories: mount the directory itself.
        src = Path(input_path)
        data_vol_src = src if src.is_dir() else src.parent

        image    = plugin["image"]
        memory   = plugin.get("memory", "1g")
        cpus     = plugin.get("cpus", "0.5")
        network  = plugin.get("network", "none")
        readonly = plugin.get("readonly", True)
        extra_tmp         = plugin.get("extra_tmpfs", [])
        windows_container = plugin.get("windows_container", False)

        envs = []
        if "env_var" in plugin:
            env_name = plugin["env_var"]
            envs += ["-e", f"{env_name}={input_type or plugin.get('default_type', 'fs')}"]

        # Always pass the original filename so entrypoints can locate the file
        # deterministically without relying on `find` ordering.
        if not src.is_dir():
            envs += ["-e", f"INPUT_FILENAME={src.name}"]

        envs += ["-e", f"JOB_ID={job_id}"]

        # â”€â”€ Base docker run flags â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        if windows_container:
            cmd = [
                "docker", "run", "--rm",
                "--network", network,
                f"--memory={memory}",
                f"--cpus={cpus}",
            ]
        else:
            cmd = [
                "docker", "run", "--rm",
                "--network", network,
                f"--memory={memory}",
                f"--cpus={cpus}",
                "--pids-limit=200",
                "--cap-drop=ALL",
                "--security-opt", "no-new-privileges",
                "--tmpfs=/tmp:rw,size=64m",
            ]
            if readonly:
                cmd.append("--read-only")
            for t in extra_tmp:
                cmd += ["--tmpfs", t]

        # Named volumes declared in plugin config (e.g. Volatility symbol cache)
        for vol in plugin.get("plugin_volumes", []):
            cmd += ["-v", vol]

        dood = _is_dood() and not windows_container

        if dood:
            # â”€â”€ DooD mode: share the worker's filesystem directly â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            # --volumes-from inherits all mounts from the worker container
            # (including .:/app which covers tmp_jobs/).  No host-path
            # translation needed â€” the child container sees the same paths
            # as the worker.
            worker_name = _WORKER_CONTAINER or "fs_worker"
            cmd += ["--volumes-from", worker_name]

            # Tell entrypoints where to find input and where to write output,
            # using paths valid inside the shared /app mount.
            envs += [
                "-e", f"INPUT_PATH={data_vol_src.resolve()}",
                "-e", f"OUTPUT_PATH={job_out.resolve()}",
            ]
        else:
            # â”€â”€ Native mode: explicit bind mounts with host-path translation â”€â”€
            data_mount   = r"C:\data"   if windows_container else "/data"
            output_mount = r"C:\output" if windows_container else "/output"
            envs += [
                "-e", f"INPUT_PATH={data_mount}",
                "-e", f"OUTPUT_PATH={output_mount}",
            ]
            cmd += [
                "-v", f"{_host_path(data_vol_src.resolve())}:{data_mount}:ro",
                "-v", f"{_host_path(job_out.resolve())}:{output_mount}",
            ]

        cmd += envs + [image]

        try:
            result = subprocess.run(cmd, check=True, text=True, capture_output=True,
                                    timeout=timeout or plugin.get("timeout", 600))
            if result.stdout:
                print(result.stdout, end="")
        except subprocess.CalledProcessError as e:
            if e.stdout:
                print(e.stdout, end="")
            raise RuntimeError(f"container failed: {e.stderr}") from e
        except subprocess.TimeoutExpired as e:
            raise RuntimeError("container timed out") from e

        return str(job_out)