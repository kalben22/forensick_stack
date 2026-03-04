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

def wait_for_input_path(path: str, timeout: float = 10.0, interval: float = 0.25) -> None:
    """
    Wait for a file to exist and be fully written by the API before the worker
    tries to read it. This prevents "file not found" or incomplete read errors
    if the worker picks up the job before the API finishes writing the file.

    Checks for file existence and stable file size (no growth) within the timeout.
    Raises TimeoutError if the file isn't ready within the timeout.
    """
    import time as _time
    p = Path(path)
    deadline = _time.monotonic() + timeout   
    while _time.monotonic() < deadline:
        if p.is_dir() and any(p.iterdir()):
            return
        if p.is_file() and p.stat().st_size > 0:
            return
        _time.sleep(interval)
    # Final check for stable file size before giving up
    if p.exists():
            raise RuntimeError(f"Input file '{path}' exists but is empty after {timeout} seconds.")
    raise TimeoutError(f"Input file '{path}' not found after {timeout} seconds.")
    
def cleanup_old_tmp_jobs(tmp_base: Path, max_age_s: int = _TMP_MAX_AGE_S) -> int:
    """
    Remove stale directories under tmp_base (job output dirs) and under
    tmp_base/uploads/ (input upload dirs) that are older than max_age_s.
    Returns the total number of directories removed.
    """
    if not tmp_base.is_dir():
        return 0
    removed = 0
    cutoff = time.time() - max_age_s

    # Clean job output dirs (direct children of tmp_base, except uploads/)
    for d in tmp_base.iterdir():
        if d.name == "uploads":
            continue
        if not d.is_dir():
            continue
        try:
            if d.stat().st_mtime < cutoff:
                shutil.rmtree(d, ignore_errors=True)
                removed += 1
        except OSError:
            pass

    # Also clean individual upload dirs inside uploads/ that are stale.
    # These are normally removed immediately after each job but this catches
    # any that were missed (e.g. worker restart mid-job).
    uploads_root = tmp_base / "uploads"
    if uploads_root.is_dir():
        for d in uploads_root.iterdir():
            if not d.is_dir():
                continue
            try:
                if d.stat().st_mtime < cutoff:
                    shutil.rmtree(d, ignore_errors=True)
                    removed += 1
            except OSError:
                pass

    return removed


def cleanup_upload_dir(input_path: str, tmp_base: Path) -> None:
    """
    Immediately remove the upload directory for a completed/failed job.
    Only deletes directories that are direct children of tmp_base/uploads/
    to avoid accidental deletions.
    """
    try:
        p = Path(input_path)
        upload_dir = p.parent if p.is_file() else p
        uploads_root = tmp_base / "uploads"
        # Safety: only delete if the directory sits directly under uploads/
        if upload_dir.parent.resolve() == uploads_root.resolve():
            shutil.rmtree(str(upload_dir), ignore_errors=True)
    except Exception:
        pass


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
            # Run temp cleanup roughly every ~50 idle cycles (â‰ˆ 5 min)
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
        #   - Linux absolute (/app/...)   â†’ kept as-is (Docker worker)
        #   - Windows absolute (C:\...)   â†’ kept as-is if worker is on Windows;
        #     if worker is on Linux the path is unusable and the job will fail
        #     with a clear error rather than a corrupt '/app/C:\\...' path.
        #   - /app/ prefix on Windows     â†’ translate to local backend_dir
        _backend_dir = Path(__file__).resolve().parent.parent
        if not Path(input_path).is_absolute() and not _WIN_ABS_RE.match(input_path):
            # Relative path (the new normal) â€” resolve against backend dir
            input_path = str(_backend_dir / input_path)
        elif platform.system() == "Windows" and input_path.startswith("/app/"):
            # Legacy: Docker-style path received by a native Windows worker
            input_path = str(_backend_dir / input_path[5:])
        # else: already absolute on the current OS â€” use as-is

        # set running
        r.hset(f"job:{job_id}", mapping={"status": "running"})

        try:
            plugin_conf = PLUGIN_REGISTRY.get(tool)
            if not plugin_conf:
                raise Exception("Plugin not registered: " + tool)

            wait_for_input_path(input_path, timeout=300.0, interval=10.0)
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

            # Cleanup output job dir
            try:
                job_dir = Path(output_dir).parent
                shutil.rmtree(str(job_dir), ignore_errors=True)
            except Exception:
                pass

            # Cleanup upload dir (the input file) â€” freed immediately after use
            cleanup_upload_dir(input_path, _TMP_BASE)

            print(f"Job {job_id} done")
        except Exception as e:
            r.hset(f"job:{job_id}", mapping={"status": "failed", "error": str(e)})
            print("Error processing job", e)
            # Cleanup upload dir even on failure to avoid disk leaks
            cleanup_upload_dir(input_path, _TMP_BASE)


if __name__ == "__main__":
    worker_loop()