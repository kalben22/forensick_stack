from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from typing import Optional

from forensicstack.core.database import get_db
from forensicstack.core import crud
from forensicstack.core.auth import get_current_user
from forensicstack.core.models.user_model import User
from forensicstack.core.minio_service import get_minio_service
from forensicstack.api.schemas import ArtifactResponse, ArtifactListResponse

router = APIRouter(prefix="/api/v1/cases/{case_id}/artifacts", tags=["artifacts"])

# Valid artifact types
ARTIFACT_TYPES = {
    "memory_dump", "disk_image", "mobile_backup", "pcap",
    "logs", "malware_sample", "document", "other",
}


@router.post("/", response_model=ArtifactResponse, status_code=201)
async def upload_artifact(
    case_id: int,
    file: UploadFile = File(...),
    artifact_type: str = Form("other"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a forensic artifact file to MinIO and register it in the database.

    - **file**: The artifact file (memory dump, disk image, mobile backup, etc.)
    - **artifact_type**: Category — memory_dump | disk_image | mobile_backup | pcap | logs | malware_sample | document | other
    """
    # Verify case exists
    db_case = crud.get_case(db, case_id)
    if not db_case:
        raise HTTPException(status_code=404, detail="Case not found")

    if artifact_type not in ARTIFACT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid artifact_type. Must be one of: {', '.join(sorted(ARTIFACT_TYPES))}",
        )

    # Read file into memory
    file_data = await file.read()
    if not file_data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # Compute hashes
    minio = get_minio_service()
    md5_hex, sha256_hex = minio.compute_hashes(file_data)

    # Build object name and upload
    object_name = minio.build_object_name(case_id, file.filename)
    minio.upload_artifact(
        file_data=file_data,
        object_name=object_name,
        content_type=file.content_type or "application/octet-stream",
    )

    # Persist artifact record in PostgreSQL
    artifact_data = {
        "case_id": case_id,
        "filename": file.filename,
        "artifact_type": artifact_type,
        "file_path": object_name,
        "file_size": len(file_data),
        "file_hash_md5": md5_hex,
        "file_hash_sha256": sha256_hex,
    }
    db_artifact = crud.create_artifact(db, artifact_data)

    # Attach a short-lived download URL
    result = ArtifactResponse.model_validate(db_artifact)
    result.download_url = minio.get_presigned_url(object_name)
    return result


@router.get("/", response_model=ArtifactListResponse)
async def list_artifacts(
    case_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """List all artifacts for a case."""
    if not crud.get_case(db, case_id):
        raise HTTPException(status_code=404, detail="Case not found")

    artifacts = crud.get_artifacts_by_case(db, case_id)
    return {"artifacts": artifacts, "total": len(artifacts)}


@router.get("/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(
    case_id: int,
    artifact_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get artifact details and a presigned download URL."""
    db_artifact = crud.get_artifact(db, artifact_id)
    if not db_artifact or db_artifact.case_id != case_id:
        raise HTTPException(status_code=404, detail="Artifact not found")

    minio = get_minio_service()
    result = ArtifactResponse.model_validate(db_artifact)
    result.download_url = minio.get_presigned_url(db_artifact.file_path)
    return result


@router.delete("/{artifact_id}", status_code=204)
async def delete_artifact(
    case_id: int,
    artifact_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Delete an artifact from both MinIO and the database."""
    db_artifact = crud.get_artifact(db, artifact_id)
    if not db_artifact or db_artifact.case_id != case_id:
        raise HTTPException(status_code=404, detail="Artifact not found")

    # Remove from MinIO
    minio = get_minio_service()
    minio.delete_artifact(db_artifact.file_path)

    # Remove analysis findings from ChromaDB (best-effort)
    try:
        from forensicstack.core.chroma_service import get_chroma_service
        get_chroma_service().delete_by_artifact(artifact_id)
    except Exception:
        pass

    # Remove from DB (cascades to analyses)
    db.delete(db_artifact)
    db.commit()
    return None
