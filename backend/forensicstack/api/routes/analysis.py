from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
import tempfile
import os

from forensicstack.core.database import get_db
from forensicstack.core import crud
from forensicstack.core.tasks import (
    analyze_memory_volatility,
    scan_yara,
    analyze_disk_tsk,
    generate_timeline_plaso
)

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])

# ============================================================
# SCHEMAS
# ============================================================

class VolatilityRequest(BaseModel):
    artifact_id: int
    plugin: str
    output_format: str = "json"

class YaraRequest(BaseModel):
    artifact_id: int
    rules_path: str

class TSKRequest(BaseModel):
    artifact_id: int
    action: str  # "partitions" or "files"
    partition_offset: Optional[int] = 0

class PlasoRequest(BaseModel):
    artifact_id: int
    output_file: str

# ============================================================
# VOLATILITY ENDPOINTS
# ============================================================

@router.get("/volatility/plugins")
async def list_volatility_plugins():
    """List all Volatility plugins"""
    from forensicstack.plugins.memory.volatility import get_volatility_plugin
    
    vol = get_volatility_plugin()
    plugins = vol.list_plugins()
    
    return {
        "total": len(plugins),
        "version": vol.version,
        "plugins": {
            "windows": [p for p in plugins if p.startswith("windows.")],
            "linux": [p for p in plugins if p.startswith("linux.")],
            "mac": [p for p in plugins if p.startswith("mac.")]
        }
    }

@router.post("/volatility")
async def start_volatility_analysis(
    request: VolatilityRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Start Volatility memory analysis
    
    Example:
        POST /api/v1/analysis/volatility
        {
            "artifact_id": 1,
            "plugin": "windows.pslist",
            "output_format": "json"
        }
    """
    # Verify artifact exists
    artifact = crud.get_artifact(db, request.artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    
    # Launch Celery task
    task = analyze_memory_volatility.delay(
        request.artifact_id,
        request.plugin,
        request.output_format
    )
    
    return {
        "status": "started",
        "task_id": task.id,
        "artifact_id": request.artifact_id,
        "plugin": request.plugin,
        "message": "Analysis started in background"
    }

# ============================================================
# YARA ENDPOINTS
# ============================================================

@router.post("/yara")
async def start_yara_scan(
    request: YaraRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Start YARA malware scan
    
    Example:
        POST /api/v1/analysis/yara
        {
            "artifact_id": 1,
            "rules_path": "/rules/malware.yar"
        }
    """
    artifact = crud.get_artifact(db, request.artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    
    task = scan_yara.delay(request.artifact_id, request.rules_path)
    
    return {
        "status": "started",
        "task_id": task.id,
        "artifact_id": request.artifact_id,
        "rules": request.rules_path
    }

# ============================================================
# TSK ENDPOINTS
# ============================================================

@router.post("/tsk")
async def start_tsk_analysis(
    request: TSKRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Start TSK disk analysis
    
    Example:
        POST /api/v1/analysis/tsk
        {
            "artifact_id": 1,
            "action": "partitions"
        }
    """
    artifact = crud.get_artifact(db, request.artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    
    task = analyze_disk_tsk.delay(
        request.artifact_id,
        request.action,
        request.partition_offset
    )
    
    return {
        "status": "started",
        "task_id": task.id,
        "artifact_id": request.artifact_id,
        "action": request.action
    }

# ============================================================
# PLASO ENDPOINTS
# ============================================================

@router.post("/plaso")
async def start_plaso_timeline(
    request: PlasoRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Start Plaso timeline generation
    
    Example:
        POST /api/v1/analysis/plaso
        {
            "artifact_id": 1,
            "output_file": "timeline.csv"
        }
    """
    artifact = crud.get_artifact(db, request.artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    
    task = generate_timeline_plaso.delay(
        request.artifact_id,
        request.output_file
    )
    
    return {
        "status": "started",
        "task_id": task.id,
        "artifact_id": request.artifact_id,
        "output_file": request.output_file
    }

# ============================================================
# TASK STATUS (commun à tous)
# ============================================================

@router.get("/status/{task_id}")
async def get_analysis_status(task_id: str):
    """Get analysis task status"""
    from celery.result import AsyncResult
    
    task = AsyncResult(task_id)
    
    response = {
        "task_id": task_id,
        "status": task.status,
        "ready": task.ready()
    }
    
    if task.ready():
        response["result"] = task.result
    
    return response
