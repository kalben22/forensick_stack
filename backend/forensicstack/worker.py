# forensicstack/worker.py
import os
import platform
import json
import time
import redis
from pathlib import Path
from dotenv import load_dotenv
from minio import Minio

load_dotenv()
from forensicstack.core.plugin_registry import PLUGIN_REGISTRY
from forensicstack.core.executor.docker_executor import DockerExecutor
from forensicstack.core.executor.native_executor import NativeExecutor
from forensicstack.core.normalization_engine import normalize

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASS = os.getenv("REDIS_PASSWORD", "")

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET = os.getenv("MINIO_SECRET_KEY")

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASS, decode_responses=True)
minio_client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS, secret_key=MINIO_SECRET, secure=False)

BUCKET = "forensic-outputs"
# create bucket if not exists
if not minio_client.bucket_exists(BUCKET):
    minio_client.make_bucket(BUCKET)


def upload_dir_to_minio(prefix: str, dir_path: str):
    import os
    for root, _, files in os.walk(dir_path):
        for fname in files:
            fpath = os.path.join(root, fname)
            object_name = f"{prefix}/{os.path.relpath(fpath, dir_path)}"
            minio_client.fput_object(BUCKET, object_name, fpath)


def worker_loop():
    print("Worker started, waiting for jobs...")
    while True:
        job = r.brpop("job_queue", timeout=5)
        if not job:
            time.sleep(1)
            continue
        job_data = json.loads(job[1])
        job_id = job_data["job_id"]
        tool = job_data["tool"]
        input_path = job_data["input_path"]
        input_type = job_data.get("input_type")

        # Normalise input_path to an absolute host path.
        # The API stores an absolute path anchored to its own runtime root
        # (Docker: /app/..., or host: C:\...\backend\...).  When the worker
        # runs on Windows but receives a Linux Docker path (/app/...), translate
        # it to the corresponding Windows path via the bind-mount equivalence
        # /app == backend_dir.
        _backend_dir = Path(__file__).resolve().parent.parent
        if platform.system() == "Windows" and input_path.startswith("/app/"):
            input_path = str(_backend_dir / input_path[5:])  # strip "/app/"
        elif not Path(input_path).is_absolute():
            input_path = str(_backend_dir / input_path)

        # set running
        r.hset(f"job:{job_id}", mapping={"status": "running"})

        try:
            plugin_conf = PLUGIN_REGISTRY.get(tool)
            if not plugin_conf:
                raise Exception("Plugin not registered: " + tool)

            # Choose executor: native (direct host subprocess) or Docker container
            if plugin_conf.get("executor") == "native":
                output_dir = NativeExecutor.run_plugin(tool, input_path, input_type=input_type)
            else:
                output_dir = DockerExecutor.run_plugin(tool, input_path, input_type=input_type)

            # normalize
            findings = normalize(tool, output_dir)  # returns list of Finding dataclasses
            # Convert findings into json-serializable dicts
            findings_json = [f.__dict__ for f in findings]

            # upload raw output to MinIO
            prefix = f"{tool}/{job_id}"
            upload_dir_to_minio(prefix, output_dir)

            # save findings into Redis (or DB later)
            r.hset(f"job:{job_id}", mapping={
                "status": "completed",
                "findings": json.dumps(findings_json),
                "output_prefix": prefix
            })

            # cleanup tmp job dir (safe)
            try:
                import shutil
                shutil.rmtree(output_dir, ignore_errors=True)
                parent = os.path.dirname(output_dir)
                # remove job parent if empty
                if os.path.isdir(parent) and not os.listdir(parent):
                    shutil.rmtree(parent, ignore_errors=True)
            except Exception:
                pass

            print(f"Job {job_id} done")
        except Exception as e:
            r.hset(f"job:{job_id}", mapping={"status": "failed", "error": str(e)})
            print("Error processing job", e)


if __name__ == "__main__":
    worker_loop()