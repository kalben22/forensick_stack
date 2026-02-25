from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from forensicstack.core.database import get_db
from forensicstack.core import crud
from forensicstack.core.tasks import analyze_memory_volatility
from forensicstack.plugins.memory.volatility_plugin import get_volatility_plugin

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])


class VolatilityAnalysisRequest(BaseModel):
    artifact_id: int
    plugin: str
    output_format: str = "json"

@router.get("/volatility/plugins")
async def list_volatility_plugins():
    """List all available Volatility plugins"""
    vol = get_volatility_plugin()
    plugins = vol.list_plugins()
    return {
        "plugins": plugins,
        "total": len(plugins),
        "version": vol.version
    }


@router.post("/volatility")
async def start_volatility_analysis(
    request: VolatilityAnalysisRequest,
    db: Session = Depends(get_db)
):
    """
    Start Volatility analysis on a memory dump
    
    Example:
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
