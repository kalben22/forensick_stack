import subprocess, uuid, shutil, os
from pathlib import Path
from forensicstack.core.plugin_registry import PLUGIN_REGISTRY

# Anchor to the backend package root — works both in Docker (/app) and on
# the Windows host, regardless of process working directory.
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent.parent
TMP_BASE = _BACKEND_DIR / "tmp_jobs"

class DockerExecutor:
    @staticmethod
    def run_plugin(tool_name: str, input_path: str, input_type: str|None = None, timeout: int|None = None):
        if tool_name not in PLUGIN_REGISTRY:
            raise ValueError("Unknown plugin: "+tool_name)
        plugin = PLUGIN_REGISTRY[tool_name]

        job_id = str(uuid.uuid4())
        job_dir = TMP_BASE / job_id
        job_in = job_dir / "input"
        job_out = job_dir / "output"
        job_in.mkdir(parents=True, exist_ok=True)
        job_out.mkdir(parents=True, exist_ok=True)

        # copy input into job dir (safer than binding host dir directly)
        src = Path(input_path)
        if src.is_dir():
            shutil.copytree(src, job_in, dirs_exist_ok=True)
        else:
            shutil.copy2(src, job_in)

        image = plugin["image"]
        memory = plugin.get("memory","1g")
        cpus = plugin.get("cpus","0.5")
        envs = []
        if "env_var" in plugin:
            env_name = plugin["env_var"]
            envs += ["-e", f"{env_name}={input_type or plugin.get('default_type','fs')}"]
        # pass JOB_ID to have predictable output filename
        envs += ["-e", f"JOB_ID={job_id}", "-e", "INPUT_PATH=/data", "-e", "OUTPUT_PATH=/output"]

        network          = plugin.get("network", "none")
        readonly         = plugin.get("readonly", True)
        extra_tmp        = plugin.get("extra_tmpfs", [])
        windows_container = plugin.get("windows_container", False)

        # Windows containers use Windows paths and don't support Linux-specific
        # security/cgroup flags (tmpfs, cap-drop, pids-limit, read-only, security-opt).
        if windows_container:
            data_mount   = r"C:\data"
            output_mount = r"C:\output"
            cmd = [
                "docker", "run", "--rm",
                "--network", network,
                f"--memory={memory}",
                f"--cpus={cpus}",
            ]
        else:
            data_mount   = "/data"
            output_mount = "/output"
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

        # Named volumes declared in plugin config (persist between runs, e.g. symbol caches)
        for vol in plugin.get("plugin_volumes", []):
            cmd += ["-v", vol]
        cmd += envs + [
            "-v", f"{job_in.resolve()}:{data_mount}:ro",
            "-v", f"{job_out.resolve()}:{output_mount}",
            image
        ]

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

        # return path to output dir (caller will upload to MinIO)
        return str(job_out)