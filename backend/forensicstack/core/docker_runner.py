import subprocess
import uuid
import os


def run_plugin(plugin_name: str, artifact_path: str):

    job_id = str(uuid.uuid4())
    container_name = f"fs_job_{job_id[:8]}"

    cmd = [
        "docker", "run", "--rm",
        "--name", container_name,
        "--network", "none",
        "--cpus", "2",
        "--memory", "4g",
        "--read-only",
        "--pids-limit=200",
        "--cap-drop=ALL",
        "--security-opt no-new-privileges",
        "-v", f"{artifact_path}:/data:ro",
        "-v", f"{os.getcwd()}/output:/output",
        f"forensicstack/{plugin_name}:0.1"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)

    return job_id