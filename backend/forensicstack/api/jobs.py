import json
import shutil
import subprocess
import uuid
import redis
import os

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASS = os.getenv("REDIS_PASSWORD", "")

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASS, decode_responses=True)


def submit_job(tool: str, input_path: str, input_type: str = None, keep_upload: bool = False) -> str:
    """
    Submit a forensic analysis job to the Redis queue.

    Args:
        tool:        Tool name matching PLUGIN_REGISTRY
        input_path:  Path to the input file/directory
        input_type:  Optional type hint (e.g. feature id for volatility)
        keep_upload: When True the worker skips upload-dir cleanup so the file
                     can be reused by subsequent /reanalyze calls.

    Returns:
        job_id (str) - can be used to poll status
    """
    job_id = str(uuid.uuid4())

    job_data = {
        "job_id": job_id,
        "tool": tool,
        "input_path": input_path,
        "input_type": input_type,
        "keep_upload": keep_upload,
    }

    # Route heavy tools (long PDB scan) to a dedicated queue so light tools
    # (aLEAPP, iLEAPP, ExifTool, EZTools) are never blocked by Volatility.
    _HEAVY_TOOLS = {"volatility"}
    queue = "job_queue_heavy" if tool in _HEAVY_TOOLS else "job_queue"

    # Enqueue job
    r.lpush(queue, json.dumps(job_data))

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


def cancel_job(job_id: str) -> dict:
    """
    Cancel a queued or running job.

    - Queued : marks status as 'cancelled' — the worker skips it on pickup.
    - Running: marks status as 'cancelled' AND sends `docker kill` to the
               container (name stored in Redis as 'container' field).

    Returns {"cancelled": True} or {"cancelled": False, "reason": "..."}
    """
    data = r.hgetall(f"job:{job_id}")
    if not data:
        return {"cancelled": False, "reason": "not_found"}

    status = data.get("status")
    if status in ("completed", "failed", "cancelled"):
        return {"cancelled": False, "reason": f"job already {status}"}

    # Mark cancelled in Redis first (worker checks this on pickup)
    r.hset(f"job:{job_id}", "status", "cancelled")

    # If the container is already running, kill it immediately
    if status == "running":
        container = data.get("container", f"fsjob-{job_id}")
        try:
            subprocess.run(
                ["docker", "kill", container],
                capture_output=True, timeout=10
            )
        except Exception:
            pass  # best-effort — the container may have already exited

    return {"cancelled": True}


# ── Upload token (reusable file sessions) ──────────────────────────────────────
# After a /direct upload, an upload_token is generated and tied to the on-disk
# file path.  Subsequent analysis requests for the same file use /reanalyze with
# this token — no re-upload required.  The token expires after 2 h of inactivity;
# the user can also explicitly discard it via DELETE /upload/{token}.

_UPLOAD_TOKEN_TTL = 2 * 3600  # 2 h


def store_upload_token(token: str, file_path: str, upload_dir: str) -> None:
    r.set(
        f"upload_token:{token}",
        json.dumps({"file_path": file_path, "upload_dir": upload_dir}),
        ex=_UPLOAD_TOKEN_TTL,
    )


def get_upload_by_token(token: str) -> dict | None:
    val = r.get(f"upload_token:{token}")
    if not val:
        return None
    return json.loads(val)


def refresh_upload_token(token: str) -> None:
    """Extend the TTL each time the file is reused for a new analysis."""
    r.expire(f"upload_token:{token}", _UPLOAD_TOKEN_TTL)


def delete_upload_token(token: str) -> None:
    """Remove the token and delete the associated upload directory from disk."""
    data = get_upload_by_token(token)
    if data:
        shutil.rmtree(data["upload_dir"], ignore_errors=True)
    r.delete(f"upload_token:{token}")


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
