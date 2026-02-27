import subprocess, uuid, shutil, os
from pathlib import Path
from forensicstack.core.plugin_registry import PLUGIN_REGISTRY

TMP_BASE = Path("tmp_jobs")

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

        cmd = [
            "docker", "run", "--rm",
            "--network", "none",
            f"--memory={memory}",
            f"--cpus={cpus}",
            "--read-only",
            "--tmpfs=/tmp:rw,size=64m",
            "--pids-limit=200",
            "--cap-drop=ALL",
            "--security-opt","no-new-privileges"
        ] + envs + [
            "-v", f"{job_in.resolve()}:/data:ro",
            "-v", f"{job_out.resolve()}:/output",
            image
        ]

        try:
            subprocess.run(cmd, check=True, text=True, capture_output=True, timeout=timeout or plugin.get("timeout",600))
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"container failed: {e.stderr}") from e
        except subprocess.TimeoutExpired as e:
            raise RuntimeError("container timed out") from e

        # return path to output dir (caller will upload to MinIO)
        return str(job_out)