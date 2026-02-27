from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from forensicstack.core.database import get_db
from forensicstack.core import crud
from forensicstack.core.auth import get_current_user
from forensicstack.core.models.user_model import User
from forensicstack.core.plugin_registry import PLUGIN_REGISTRY
from forensicstack.api.jobs import submit_job, get_job_status
from forensicstack.api.schemas import JobSubmitRequest, JobStatusResponse

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


@router.get("/tools")
async def list_tools(_: User = Depends(get_current_user)):
    """
    List all available forensic tools registered in the plugin registry.
    These are the valid values for the `tool` field in /jobs/submit.
    """
    tools = []
    for name, config in PLUGIN_REGISTRY.items():
        tools.append({
            "name": name,
            "category": config.get("category"),
            "image": config.get("image"),
            "memory": config.get("memory"),
            "cpus": config.get("cpus"),
            "timeout_seconds": config.get("timeout"),
        })
    return {"tools": tools, "total": len(tools)}


@router.post("/submit", response_model=JobStatusResponse, status_code=202)
async def submit(
    request: JobSubmitRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Submit a forensic analysis job to the Redis worker queue.

    The worker will:
    1. Pull the job from the queue
    2. Run the specified tool in an isolated Docker container
    3. Normalise the output into Finding objects
    4. Upload raw results to MinIO
    5. Store findings in Redis (poll /jobs/{job_id} for results)

    Returns a `job_id` you can use to poll status via `GET /api/v1/jobs/{job_id}`.
    """
    if request.tool not in PLUGIN_REGISTRY:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown tool '{request.tool}'. Available: {list(PLUGIN_REGISTRY.keys())}",
        )

    artifact = crud.get_artifact(db, request.artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    job_id = submit_job(
        tool=request.tool,
        input_path=artifact.file_path,
        input_type=request.input_type,
    )

    return {
        "job_id": job_id,
        "status": "queued",
        "findings": None,
        "output_prefix": None,
        "error": None,
    }


@router.get("/{job_id}", response_model=JobStatusResponse)
async def job_status(
    job_id: str,
    _: User = Depends(get_current_user),
):
    """
    Poll the status of a previously submitted job.

    Possible statuses:
    - **queued**    — waiting to be picked up by a worker
    - **running**   — currently being processed
    - **completed** — finished; `findings` and `output_prefix` are populated
    - **failed**    — error occurred; `error` contains the message
    - **not_found** — unknown job ID
    """
    result = get_job_status(job_id)
    return {"job_id": job_id, **result}
