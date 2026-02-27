import json
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
