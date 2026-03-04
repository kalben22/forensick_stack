import json
import shutil
import uuid
import redis
import os

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASS = os.getenv("REDIS_PASSWORD", "")

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASS, decode_responses=True)


def submit_job(tool: str, input_path: str, input_type: str = None) -> str:
    """
    Submit a forensic analysis job to the Redis queue.

    Args:
        tool:       Tool name matching PLUGIN_REGISTRY (ileapp, aleapp, exiftool, volatility)
        input_path: Absolute path to the input file/directory
        input_type: Optional type hint passed to the container (e.g. "fs", "tar")

    Returns:
        job_id (str) - can be used to poll status
    """
    job_id = str(uuid.uuid4())

    job_data = {
        "job_id": job_id,
        "tool": tool,
        "input_path": input_path,
        "input_type": input_type,
    }

    # Enqueue job
    r.lpush("job_queue", json.dumps(job_data))

    # Set initial status
    r.hset(f"job:{job_id}", mapping={"status": "queued"})

    return job_id


def get_job_status(job_id: str) -> dict:
    """
    Get current status of a submitted job.

    Returns dict with keys: status, findings (if done), error (if failed)
    """
    data = r.hgetall(f"job:{job_id}")
    if not data:
        return {"status": "not_found"}

    result = {"status": data.get("status", "unknown")}

    if "findings" in data:
        result["findings"] = json.loads(data["findings"])

    if "output_prefix" in data:
        result["output_prefix"] = data["output_prefix"]

    if "error" in data:
        result["error"] = data["error"]

    return result


# ── Upload tracking ────────────────────────────────────────────────────────────
# When a user submits a new /direct analysis, the previous upload directory for
# that user is cleaned up if the previous job has already completed or failed.
# This frees disk space immediately instead of waiting for the stale-cleanup TTL.

_UPLOAD_TRACK_TTL = 4 * 3600  # 4 h — safety net in case the job never completes


def track_user_upload(user_id: int, job_id: str, upload_dir: str) -> None:
    """Record the user's latest upload so it can be cleaned on the next request."""
    r.set(f"upload_track:{user_id}", f"{job_id}|{upload_dir}", ex=_UPLOAD_TRACK_TTL)


def cleanup_prev_user_upload(user_id: int) -> None:
    """
    Delete the previous upload directory for this user if its job is done.
    Safe to call before writing a new upload — only acts on completed/failed jobs.
    """
    prev = r.get(f"upload_track:{user_id}")
    if not prev:
        return
    try:
        prev_job_id, prev_dir = prev.split("|", 1)
        prev_status = r.hget(f"job:{prev_job_id}", "status")
        if prev_status in ("completed", "failed"):
            shutil.rmtree(prev_dir, ignore_errors=True)
            r.delete(f"upload_track:{user_id}")
    except Exception:
        pass
