import os
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from forensicstack.core.database import get_db
from forensicstack.core import crud
from forensicstack.core.auth import get_current_user
from forensicstack.core.models.user_model import User
from forensicstack.core.plugin_registry import PLUGIN_REGISTRY
from forensicstack.api.jobs import (
    submit_job, get_job_status, cancel_job,
    store_upload_token, get_upload_by_token, refresh_upload_token, delete_upload_token,
    cleanup_prev_user_upload, track_user_upload,
)
from forensicstack.api.schemas import JobSubmitRequest, JobStatusResponse

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


@router.get("/tools")
async def list_tools(_: User = Depends(get_current_user)):
    """
    List all available forensic tools registered in the plugin registry,
    including their features (specific commands/sub-analyses).
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
            "features": config.get("features", []),
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


@router.post("/direct", status_code=202)
async def direct_analyze(
    file: UploadFile = File(...),
    tool: str = Form(...),
    feature: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a file and immediately submit a forensic analysis job.

    No case management required — the file is written to a temporary
    directory accessible by the worker and cleaned up after the job runs.

    - **file**: the artifact to analyse (memory dump, mobile backup, etc.)
    - **tool**: tool name from the plugin registry (volatility, exiftool, …)
    - **feature**: specific feature/plugin to run (e.g. windows.pslist for volatility)
    """
    if tool not in PLUGIN_REGISTRY:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown tool '{tool}'. Available: {list(PLUGIN_REGISTRY.keys())}",
        )

    MAX_UPLOAD_BYTES = 5 * 1024 ** 3  # 5 GB

    # If the user has a previous completed/failed upload, free its disk space now.
    cleanup_prev_user_upload(current_user.id)

    # Write the uploaded file to a local temp dir (shared with the worker).
    # Use __file__-based absolute path so it resolves correctly regardless of
    # whether the API runs in Docker (/app) or directly on the host.
    # Stream in 1 MB chunks so a 5 GB dump never fully resides in RAM.
    _backend_dir = Path(__file__).resolve().parent.parent.parent.parent
    upload_dir = _backend_dir / "tmp_jobs" / "uploads" / str(uuid4())
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_filename = Path(file.filename).name if file.filename else "upload"
    file_path = upload_dir / safe_filename

    written = 0
    with open(file_path, "wb") as out:
        while True:
            chunk = await file.read(1024 * 1024)  # 1 MB per read
            if not chunk:
                break
            written += len(chunk)
            if written > MAX_UPLOAD_BYTES:
                file_path.unlink(missing_ok=True)
                upload_dir.rmdir()
                raise HTTPException(status_code=413, detail="File exceeds the 5 GB upload limit.")
            out.write(chunk)
        out.flush()
        os.fsync(out.fileno())

    # Store path RELATIVE to _backend_dir so the worker resolves it correctly
    # regardless of its own runtime (Docker/Linux vs native/Windows).
    # Storing an absolute path causes '/app/C:\\...' corruption when the API
    # runs on Windows but the worker is inside a Linux Docker container.
    try:
        rel = file_path.resolve().relative_to(_backend_dir)
        stored_path = rel.as_posix()   # e.g. "tmp_jobs/uploads/{uuid}/file.mem"
    except ValueError:
        stored_path = str(file_path.resolve())

    # Generate a reuse token so subsequent features on this file skip re-upload.
    upload_token = str(uuid4())
    store_upload_token(upload_token, stored_path, str(upload_dir))

    job_id = submit_job(
        tool=tool,
        input_path=stored_path,
        input_type=feature,
        keep_upload=True,   # worker must NOT delete — the token owns the dir
    )

    # Track this upload so the next /direct call for this user can clean it up.
    track_user_upload(current_user.id, job_id, str(upload_dir))

    return {
        "job_id": job_id,
        "filename": safe_filename,
        "size_bytes": written,
        "tool": tool,
        "feature": feature,
        "upload_token": upload_token,
    }


@router.post("/reanalyze", status_code=202)
async def reanalyze(
    upload_token: str = Form(...),
    tool: str = Form(...),
    feature: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
):
    """
    Submit a new analysis job for an already-uploaded file.

    Uses the `upload_token` returned by a previous `/direct` call.
    No file upload required — the file stays on disk between analyses.

    - **upload_token**: token from the previous `/direct` response
    - **tool**: tool name (same or different from the original upload)
    - **feature**: specific feature/plugin to run
    """
    if tool not in PLUGIN_REGISTRY:
        raise HTTPException(status_code=400, detail=f"Unknown tool '{tool}'.")

    upload_info = get_upload_by_token(upload_token)
    if not upload_info:
        raise HTTPException(
            status_code=404,
            detail="Upload token not found or expired. Please re-upload the file.",
        )

    # Extend TTL so an active session stays alive
    refresh_upload_token(upload_token)

    job_id = submit_job(
        tool=tool,
        input_path=upload_info["file_path"],
        input_type=feature,
        keep_upload=True,
    )

    return {"job_id": job_id, "tool": tool, "feature": feature, "upload_token": upload_token}


@router.delete("/upload/{token}")
async def delete_upload(
    token: str,
    _: User = Depends(get_current_user),
):
    """
    Explicitly release a reusable upload session.

    Deletes the on-disk file and the Redis token.  Call this when the user
    clicks "Changer de fichier" so disk space is freed immediately.
    """
    delete_upload_token(token)
    return {"deleted": True}


@router.delete("/{job_id}")
async def cancel(
    job_id: str,
    _: User = Depends(get_current_user),
):
    """
    Cancel a queued or running job.

    - **queued** jobs are marked cancelled and skipped by the worker.
    - **running** jobs have their Docker container killed immediately.

    Returns `{"cancelled": true}` on success, or `{"cancelled": false, "reason": "..."}`.
    """
    result = cancel_job(job_id)
    if not result["cancelled"] and result.get("reason") == "not_found":
        raise HTTPException(status_code=404, detail="Job not found")
    return result


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
