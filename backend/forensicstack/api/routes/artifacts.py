import hashlib
import logging
import os
import tempfile
from functools import partial

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from forensicstack.api.schemas import ArtifactListResponse, ArtifactResponse
from forensicstack.core import crud
from forensicstack.core.auth import get_current_user, owner_scope
from forensicstack.core.database import get_db
from forensicstack.core.minio_service import (
    ARTIFACTS_BUCKET,
    MAX_UPLOAD_BYTES,
    SAFE_CONTENT_TYPE,
    get_minio_service,
    sanitize_filename,
)
from forensicstack.core.models.user_model import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/cases/{case_id}/artifacts", tags=["artifacts"])

# Valid artifact types
ARTIFACT_TYPES = {
    "memory_dump", "disk_image", "mobile_backup", "pcap",
    "logs", "malware_sample", "document", "other",
}

# Read size for the multipart stream.
CHUNK_SIZE = 1024 * 1024  # 1 MB


# NOTE ON HANDLER STYLE
# The read-only/delete handlers are plain `def`: their psycopg2 and MinIO calls
# block, and running them as `async def` executed that blocking I/O on the event
# loop, stalling every other request in this single-process API. Only
# upload_artifact stays `async` — it genuinely awaits the multipart stream — and
# it pushes its blocking storage/DB work to the threadpool.


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
    # Ownership is checked before a single byte is accepted: without this, any
    # account could push evidence into another investigator's case.
    db_case = await run_in_threadpool(
        partial(crud.get_case, db, case_id, owner_id=owner_scope(current_user))
    )
    if not db_case:
        raise HTTPException(status_code=404, detail="Case not found")

    if artifact_type not in ARTIFACT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid artifact_type. Must be one of: {', '.join(sorted(ARTIFACT_TYPES))}",
        )

    # `Path(name).name` (same treatment as /jobs/direct): the raw multipart
    # filename went straight into the object key, so "../case-7/dump.raw" or an
    # absolute path could write outside this case's prefix and clobber another
    # case's evidence.
    safe_filename = sanitize_filename(file.filename)

    # Stream to a temp file, hashing as we go. The previous `await file.read()`
    # materialised the entire upload in RAM: a 5 GB disk image meant a 5 GB
    # allocation, and a few concurrent uploads OOM-killed the API process.
    md5 = hashlib.md5(usedforsecurity=False)
    sha256 = hashlib.sha256()
    written = 0
    tmp_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".upload") as tmp:
            tmp_path = tmp.name
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                written += len(chunk)
                if written > MAX_UPLOAD_BYTES:
                    # Enforced while streaming, so an oversized upload is cut
                    # off instead of filling the disk and then being rejected.
                    raise HTTPException(
                        status_code=413,
                        detail=(
                            f"File exceeds the maximum upload size of "
                            f"{MAX_UPLOAD_BYTES} bytes."
                        ),
                    )
                md5.update(chunk)
                sha256.update(chunk)
                tmp.write(chunk)
            tmp.flush()
            os.fsync(tmp.fileno())

        if written == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")

        md5_hex = md5.hexdigest()
        sha256_hex = sha256.hexdigest()

        minio = get_minio_service()
        # Content-addressed key: the old case-{id}/{filename} scheme meant a
        # second upload of "dump.raw" silently overwrote the bytes of the first
        # artifact while the DB kept both rows — evidence destruction in a
        # chain-of-custody product.
        object_name = minio.build_object_name(case_id, safe_filename, sha256_hex)

        # content_type is forced to application/octet-stream: storing the
        # client-supplied value and replaying it on the presigned download URL
        # turned an uploaded .html into stored XSS against investigators.
        await run_in_threadpool(
            partial(
                minio.upload_file,
                tmp_path,
                object_name,
                bucket=ARTIFACTS_BUCKET,
                content_type=SAFE_CONTENT_TYPE,
            )
        )
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError as e:
                logger.warning("Could not remove temp upload %s: %s", tmp_path, e)

    artifact_data = {
        "case_id": case_id,
        "filename": safe_filename,
        "artifact_type": artifact_type,
        "file_path": object_name,
        "file_size": written,
        "file_hash_md5": md5_hex,
        "file_hash_sha256": sha256_hex,
    }
    db_artifact = await run_in_threadpool(
        partial(crud.create_artifact, db, artifact_data)
    )

    # Attach a short-lived download URL
    result = ArtifactResponse.model_validate(db_artifact)
    result.download_url = await run_in_threadpool(
        partial(minio.get_presigned_url, object_name)
    )
    return result


@router.get("/", response_model=ArtifactListResponse)
def list_artifacts(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all artifacts for a case you own."""
    scope = owner_scope(current_user)
    # Ownership is verified through the parent case; artifacts have no owner of
    # their own. Without this, any account could enumerate every case's evidence
    # inventory (filenames and hashes).
    if not crud.get_case(db, case_id, owner_id=scope):
        raise HTTPException(status_code=404, detail="Case not found")

    artifacts = crud.get_artifacts_by_case(db, case_id, owner_id=scope)
    return {"artifacts": artifacts, "total": len(artifacts)}


@router.get("/{artifact_id}", response_model=ArtifactResponse)
def get_artifact(
    case_id: int,
    artifact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get artifact details and a presigned download URL."""
    db_artifact = crud.get_case_artifact(
        db, case_id, artifact_id, owner_id=owner_scope(current_user)
    )
    if not db_artifact:
        # 404 rather than 403 — see cases.get_case. This endpoint mints a
        # presigned MinIO URL, so an ownership miss here handed out a working
        # download link to somebody else's evidence.
        raise HTTPException(status_code=404, detail="Artifact not found")

    minio = get_minio_service()
    result = ArtifactResponse.model_validate(db_artifact)
    result.download_url = minio.get_presigned_url(db_artifact.file_path)
    return result


@router.delete("/{artifact_id}", status_code=204)
def delete_artifact(
    case_id: int,
    artifact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an artifact from both MinIO and the database."""
    db_artifact = crud.get_case_artifact(
        db, case_id, artifact_id, owner_id=owner_scope(current_user)
    )
    if not db_artifact:
        # Previously any authenticated account could destroy any artifact in the
        # platform, MinIO object included — irreversible evidence loss.
        raise HTTPException(status_code=404, detail="Artifact not found")

    object_name = db_artifact.file_path
    # Keys are content-addressed, so two identical uploads share one object.
    # Only drop the bytes when no other row still points at them.
    shared = (
        crud.count_artifacts_sharing_path(db, object_name, artifact_id)
        if object_name
        else 0
    )

    # Remove from DB first (cascades to analyses); storage cleanup is
    # best-effort afterwards.
    db.delete(db_artifact)
    db.commit()

    if object_name and shared == 0:
        try:
            get_minio_service().delete_artifact(object_name)
        except Exception as e:
            logger.warning("Artifact %s: MinIO cleanup failed: %s", artifact_id, e)

    # Remove analysis findings from ChromaDB (best-effort)
    try:
        from forensicstack.core.chroma_service import get_chroma_service

        get_chroma_service().delete_by_artifact(artifact_id)
    except Exception as e:
        logger.warning("Artifact %s: ChromaDB cleanup failed: %s", artifact_id, e)

    return None
