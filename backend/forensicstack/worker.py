# forensicstack/worker.py
import os
import platform
import re
import json
import time
import shutil
import redis
from pathlib import Path
from dotenv import load_dotenv
from minio import Minio

# Regex to detect Windows-style absolute paths (C:\... or C:/...)
_WIN_ABS_RE = re.compile(r'^[A-Za-z]:[/\\]')

# Remove job temp dirs older than this many seconds (default: 24 h)
_TMP_MAX_AGE_S = int(os.getenv("TMP_MAX_AGE_HOURS", "24")) * 3600

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


def cleanup_old_tmp_jobs(tmp_base: Path, max_age_s: int = _TMP_MAX_AGE_S) -> int:
    """
    Remove job execution dirs under tmp_base that are older than max_age_s.
    Only removes subdirectories of tmp_base that look like UUID job dirs
    (not the uploads/ subdir — that's cleaned by the job itself).
    Returns the number of directories removed.
    """
    if not tmp_base.is_dir():
        return 0
    removed = 0
    cutoff = time.time() - max_age_s
    for d in tmp_base.iterdir():
        if d.name == "uploads":          # keep the uploads subdir
            continue
        if not d.is_dir():
            continue
        try:
            if d.stat().st_mtime < cutoff:
                shutil.rmtree(d, ignore_errors=True)
                removed += 1
        except OSError:
            pass
    return removed


def upload_dir_to_minio(prefix: str, dir_path: str):
    import os
    for root, _, files in os.walk(dir_path):
        for fname in files:
            fpath = os.path.join(root, fname)
            object_name = f"{prefix}/{os.path.relpath(fpath, dir_path)}"
            minio_client.fput_object(BUCKET, object_name, fpath)


def worker_loop():
    print("Worker started, waiting for jobs...")
    _cleanup_counter = 0
    _TMP_BASE = Path(__file__).resolve().parent.parent / "tmp_jobs"

    while True:
        job = r.brpop("job_queue", timeout=5)
        if not job:
            time.sleep(1)
            # Run temp cleanup roughly every ~50 idle cycles (≈ 5 min)
            _cleanup_counter += 1
            if _cleanup_counter >= 50:
                _cleanup_counter = 0
                removed = cleanup_old_tmp_jobs(_TMP_BASE)
                if removed:
                    print(f"[cleanup] Removed {removed} stale tmp_jobs dirs (>{_TMP_MAX_AGE_S//3600}h old)")
            continue
        job_data = json.loads(job[1])
        job_id = job_data["job_id"]
        tool = job_data["tool"]
        input_path = job_data["input_path"]
        input_type = job_data.get("input_type")

        # Resolve input_path to an absolute path usable by this worker process.
        #
        # The API now stores paths RELATIVE to its _backend_dir (e.g.
        # "tmp_jobs/uploads/{uuid}/file.mem").  Relative paths are resolved
        # via _backend_dir on whichever OS the worker runs on.
        #
        # Legacy absolute paths (stored before this fix) are handled too:
        #   - Linux absolute (/app/...)   → kept as-is (Docker worker)
        #   - Windows absolute (C:\...)   → kept as-is if worker is on Windows;
        #     if worker is on Linux the path is unusable and the job will fail
        #     with a clear error rather than a corrupt '/app/C:\\...' path.
        #   - /app/ prefix on Windows     → translate to local backend_dir
        _backend_dir = Path(__file__).resolve().parent.parent
        if not Path(input_path).is_absolute() and not _WIN_ABS_RE.match(input_path):
            # Relative path (the new normal) — resolve against backend dir
            input_path = str(_backend_dir / input_path)
        elif platform.system() == "Windows" and input_path.startswith("/app/"):
            # Legacy: Docker-style path received by a native Windows worker
            input_path = str(_backend_dir / input_path[5:])
        # else: already absolute on the current OS — use as-is

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