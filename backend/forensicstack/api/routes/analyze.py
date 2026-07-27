"""
Automatic analysis endpoint.

The point of the platform, expressed as one call: upload a file — any file —
and the system works out what it is and what to run on it.

Before this, the analyst had to already know the answer: pick the tool, pick the
feature, and hope the extension matched a hardcoded list. Nothing identified the
artifact, and nothing chained tools. ``POST /api/v1/analyze`` closes that gap:

    upload → identify (by content) → plan (from plugin manifests) → enqueue

The plan is returned synchronously, so the UI can show "this is a Windows memory
image, here are the 6 analyses queued for it" immediately, while the jobs run.
"""

from __future__ import annotations

import logging
import os
import shutil
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.concurrency import run_in_threadpool

from forensicstack.core.auth import get_current_user
from forensicstack.core.models.user_model import User
from forensicstack.core.plugins.registry import (
    PluginRegistry,
    UnknownPluginError,
    get_registry,
)
from forensicstack.core.queue import JobMessage, JobQueue
from forensicstack.core.triage.identify import identify
from forensicstack.core.triage.router import plan_for, suggest_tools

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/analyze", tags=["analyze"])

CHUNK = 1024 * 1024
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(5 * 1024**3)))

_BACKEND_DIR = Path(__file__).resolve().parents[3]
UPLOAD_ROOT = Path(
    os.getenv("FORENSICSTACK_UPLOAD_ROOT", str(_BACKEND_DIR / "tmp_jobs" / "uploads"))
)

_queue: JobQueue | None = None


def get_queue() -> JobQueue:
    global _queue
    if _queue is None:
        _queue = JobQueue()
    return _queue


async def _stream_to_disk(file: UploadFile, dest_dir: Path) -> Path:
    """Write the upload to disk in bounded memory.

    ``routes/artifacts.py`` used to do ``await file.read()`` — the whole file
    into one buffer — so peak RSS tracked file size and a multi-GB upload could
    OOM a container that has no memory limit.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename).name if file.filename else "upload.bin"
    if not safe_name or safe_name in {".", ".."}:
        safe_name = "upload.bin"
    target = dest_dir / safe_name

    written = 0
    try:
        with target.open("wb") as out:
            while True:
                chunk = await file.read(CHUNK)
                if not chunk:
                    break
                written += len(chunk)
                if written > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"file exceeds the {MAX_UPLOAD_BYTES} byte upload limit",
                    )
                out.write(chunk)
            out.flush()
            # The worker may pick the job up the instant it is queued; fsync so
            # it cannot observe a partially-written file.
            os.fsync(out.fileno())
    except Exception:
        shutil.rmtree(dest_dir, ignore_errors=True)
        raise

    if written == 0:
        shutil.rmtree(dest_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail="uploaded file is empty")
    return target


@router.post("", status_code=202)
@router.post("/", status_code=202, include_in_schema=False)
async def analyze(
    file: Annotated[UploadFile, File(description="Artifact of any type")],
    case_id: Annotated[int | None, Form()] = None,
    auto: Annotated[bool, Form()] = True,
    max_steps: Annotated[int, Form()] = 12,
    current_user: User = Depends(get_current_user),
    reg: PluginRegistry = Depends(get_registry),
    queue: JobQueue = Depends(get_queue),
):
    """Upload an artifact, identify it, and queue the analyses that fit it."""
    plan_id = uuid.uuid4().hex
    upload_dir = UPLOAD_ROOT / plan_id
    target = await _stream_to_disk(file, upload_dir)

    # Identification reads bounded windows plus a streaming hash — cheap enough
    # to do inline, but it is CPU work, so keep it off the event loop.
    identity = await run_in_threadpool(
        identify, target, original_filename=file.filename
    )
    plan = await run_in_threadpool(
        plan_for, identity, reg=reg, max_steps=max(1, min(max_steps, 32))
    )

    queued: list[dict] = []
    if auto and plan.steps:
        messages = [
            JobMessage(
                job_id=uuid.uuid4().hex,
                tool=step.tool,
                feature=step.feature,
                input_path=str(target),
                artifact_sha256=identity.sha256,
                case_id=case_id,
                user_id=current_user.id,
                plan_id=plan_id,
                priority=step.priority,
            )
            for step in plan.steps
        ]
        await run_in_threadpool(queue.submit_many, messages)
        queued = [
            {"job_id": m.job_id, "tool": m.tool, "feature": m.feature, "priority": m.priority}
            for m in messages
        ]

    return {
        "plan_id": plan_id,
        "filename": Path(target).name,
        "identity": identity.to_dict(),
        "plan": plan.to_dict(),
        "queued_jobs": queued,
        "suggestions": suggest_tools(identity, reg=reg),
        "advice": _advice(identity),
    }


@router.post("/identify")
async def identify_only(
    file: Annotated[UploadFile, File()],
    current_user: User = Depends(get_current_user),
    reg: PluginRegistry = Depends(get_registry),
):
    """Dry run: identify and plan, queue nothing.

    Useful for the UI ("what would you do with this?") and for testing routing
    rules without spending container time.
    """
    tmp_dir = UPLOAD_ROOT / f"identify-{uuid.uuid4().hex}"
    target = await _stream_to_disk(file, tmp_dir)
    try:
        identity = await run_in_threadpool(identify, target, original_filename=file.filename)
        plan = await run_in_threadpool(plan_for, identity, reg=reg)
        return {
            "identity": identity.to_dict(),
            "plan": plan.to_dict(),
            "suggestions": suggest_tools(identity, reg=reg),
            "advice": _advice(identity),
        }
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@router.get("/tools")
def list_tools(reg: PluginRegistry = Depends(get_registry), _: User = Depends(get_current_user)):
    """Tool catalogue, built from the plugin manifests.

    Replaces the hand-maintained ``PLUGIN_REGISTRY`` dict *and* the 407-line
    hardcoded tool list the frontend carried, both of which drifted from what
    was actually installed.
    """
    return {"tools": reg.to_api_list(), "total": len(reg)}


@router.get("/plan/{plan_id}")
def plan_status(
    plan_id: str,
    _: User = Depends(get_current_user),
    queue: JobQueue = Depends(get_queue),
):
    """Aggregate status of every job queued under one plan."""
    # Job ids are recorded on the plan hash at submit time by the worker.
    raw = queue.r.smembers(f"plan:{plan_id}:jobs")
    if not raw:
        raise HTTPException(status_code=404, detail="unknown plan")
    jobs = []
    for job_id in sorted(raw):
        status = queue.get_status(job_id)
        if status:
            jobs.append({"job_id": job_id, **status})
    done = sum(1 for j in jobs if j.get("status") in {"completed", "failed"})
    return {
        "plan_id": plan_id,
        "jobs": jobs,
        "total": len(jobs),
        "finished": done,
        "progress": round(done / len(jobs), 3) if jobs else 0.0,
    }


@router.get("/queue")
def queue_stats(_: User = Depends(get_current_user), queue: JobQueue = Depends(get_queue)):
    return queue.stats()


@router.get("/suggest")
def suggest_for_kind(
    kind: str = Query(..., description="ArtifactKind value, e.g. memory_dump"),
    reg: PluginRegistry = Depends(get_registry),
    _: User = Depends(get_current_user),
):
    from forensicstack.core.triage.identify import ArtifactIdentity
    from forensicstack.core.triage.kinds import ArtifactKind

    try:
        artifact_kind = ArtifactKind(kind)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"unknown kind {kind!r}; see /api/v1/analyze/kinds",
        ) from None
    identity = ArtifactIdentity(kind=artifact_kind, confidence=1.0)
    return {"kind": kind, "suggestions": suggest_tools(identity, reg=reg)}


@router.get("/kinds")
def list_kinds(_: User = Depends(get_current_user)):
    from forensicstack.core.triage.kinds import ArtifactKind

    return {
        "kinds": [
            {"value": k.value, "family": k.family.value} for k in ArtifactKind
        ]
    }


def _advice(identity) -> str:
    from forensicstack.core.triage.router import FAMILY_ADVICE

    return FAMILY_ADVICE.get(identity.family, "")


__all__ = ["router", "UnknownPluginError"]
