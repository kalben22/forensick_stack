from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from forensicstack.core.database import get_db
from forensicstack.core import crud
from forensicstack.core.auth import get_current_user
from forensicstack.core.models.user_model import User
from forensicstack.core.tasks import (
    analyze_memory_volatility,
    scan_yara,
    analyze_disk_tsk,
    generate_timeline_plaso,
)

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])

# ── Inline request schemas ─────────────────────────────────────────────────────

class VolatilityRequest(BaseModel):
    artifact_id: int
    plugin: str
    output_format: str = "json"

class YaraRequest(BaseModel):
    artifact_id: int
    rules_path: str

class TSKRequest(BaseModel):
    artifact_id: int
    action: str          # "partitions" | "files" | "timeline"
    partition_offset: Optional[int] = 0

class PlasoRequest(BaseModel):
    artifact_id: int
    output_file: str


# ── Volatility ─────────────────────────────────────────────────────────────────

@router.get("/volatility/plugins")
async def list_volatility_plugins(_: User = Depends(get_current_user)):
    """List all available Volatility 3 plugins."""
    from forensicstack.plugins.memory.volatility import get_volatility_plugin
    vol = get_volatility_plugin()
    plugins = vol.list_plugins()
    return {
        "total": len(plugins),
        "version": vol.version,
        "plugins": {
            "windows": [p for p in plugins if p.startswith("windows.")],
            "linux":   [p for p in plugins if p.startswith("linux.")],
            "mac":     [p for p in plugins if p.startswith("mac.")],
        },
    }

@router.post("/volatility")
async def start_volatility_analysis(
    request: VolatilityRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Start an asynchronous Volatility 3 memory analysis."""
    artifact = crud.get_artifact(db, request.artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    task = analyze_memory_volatility.delay(
        request.artifact_id, request.plugin, request.output_format
    )
    return {
        "status": "started",
        "task_id": task.id,
        "artifact_id": request.artifact_id,
        "plugin": request.plugin,
    }


# ── YARA ───────────────────────────────────────────────────────────────────────

@router.post("/yara")
async def start_yara_scan(
    request: YaraRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Start an asynchronous YARA malware scan."""
    artifact = crud.get_artifact(db, request.artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    task = scan_yara.delay(request.artifact_id, request.rules_path)
    return {
        "status": "started",
        "task_id": task.id,
        "artifact_id": request.artifact_id,
        "rules": request.rules_path,
    }


# ── TSK ────────────────────────────────────────────────────────────────────────

@router.post("/tsk")
async def start_tsk_analysis(
    request: TSKRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Start an asynchronous disk image analysis with The Sleuth Kit."""
    artifact = crud.get_artifact(db, request.artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    task = analyze_disk_tsk.delay(
        request.artifact_id, request.action, request.partition_offset
    )
    return {
        "status": "started",
        "task_id": task.id,
        "artifact_id": request.artifact_id,
        "action": request.action,
    }


# ── Plaso ──────────────────────────────────────────────────────────────────────

@router.post("/plaso")
async def start_plaso_timeline(
    request: PlasoRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Start an asynchronous forensic super-timeline with Plaso."""
    artifact = crud.get_artifact(db, request.artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    task = generate_timeline_plaso.delay(request.artifact_id, request.output_file)
    return {
        "status": "started",
        "task_id": task.id,
        "artifact_id": request.artifact_id,
        "output_file": request.output_file,
    }


# ── Task Status ────────────────────────────────────────────────────────────────

@router.get("/status/{task_id}")
async def get_analysis_status(
    task_id: str,
    _: User = Depends(get_current_user),
):
    """Get the status and result of an async Celery analysis task."""
    from celery.result import AsyncResult
    task = AsyncResult(task_id)
    response = {"task_id": task_id, "status": task.status, "ready": task.ready()}
    if task.ready():
        response["result"] = task.result
    return response
