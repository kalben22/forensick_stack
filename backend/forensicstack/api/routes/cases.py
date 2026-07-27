import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from forensicstack.api.schemas import (
    CaseCreate,
    CaseListResponse,
    CaseResponse,
    CaseUpdate,
)
from forensicstack.core import crud
from forensicstack.core.auth import get_current_user, owner_scope, require_admin
from forensicstack.core.database import get_db
from forensicstack.core.models.user_model import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])


# NOTE ON HANDLER STYLE
# Every handler here is a plain `def`, not `async def`. The bodies do blocking
# psycopg2 and MinIO I/O; declaring them `async` ran that blocking work directly
# on the event loop, so a single slow query or object-storage call froze the
# whole single-process API for every other client. As plain `def`, FastAPI
# dispatches them to its threadpool.


@router.get("/", response_model=CaseListResponse)
def list_cases(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List the cases you own (admins see all), with pagination."""
    # Scoped to the caller: the previous unscoped query returned every case in
    # the platform, including other investigators' titles and case numbers.
    scope = owner_scope(current_user)
    cases = crud.get_cases(db, skip=skip, limit=limit, owner_id=scope)
    total = crud.get_cases_count(db, owner_id=scope)
    return {
        "cases": cases,
        "total": total,
        "page": skip // limit + 1 if limit > 0 else 1,
        "page_size": limit,
    }


@router.get("/admin/all", response_model=CaseListResponse)
def list_all_cases(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """
    List every case across all owners. Admin only.

    Declared before /{case_id} so the literal path wins the match. Cross-tenant
    access is an explicit, separately authorised endpoint rather than an
    implicit side effect of any authenticated request.
    """
    cases = crud.get_cases(db, skip=skip, limit=limit, owner_id=None)
    total = crud.get_cases_count(db, owner_id=None)
    return {
        "cases": cases,
        "total": total,
        "page": skip // limit + 1 if limit > 0 else 1,
        "page_size": limit,
    }


@router.post("/", response_model=CaseResponse, status_code=201)
def create_case(
    case: CaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new investigation case owned by the caller."""
    # The authenticated identity — never a client-supplied field — decides
    # ownership, so a case cannot be created on someone else's behalf.
    return crud.create_case(db, case, owner_id=current_user.id)


@router.get("/{case_id}", response_model=CaseResponse)
def get_case(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get case details by ID."""
    db_case = crud.get_case(db, case_id, owner_id=owner_scope(current_user))
    if not db_case:
        # 404, not 403: a 403 would confirm that a case with this id exists and
        # belongs to someone else, letting anyone enumerate the case-id space
        # and learn how many investigations the platform holds.
        raise HTTPException(status_code=404, detail="Case not found")
    return db_case


@router.patch("/{case_id}", response_model=CaseResponse)
def update_case(
    case_id: int,
    case_update: CaseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a case you own."""
    # Previously any account could rewrite the title/status of any case —
    # tampering with another investigator's record.
    db_case = crud.update_case(
        db, case_id, case_update, owner_id=owner_scope(current_user)
    )
    if not db_case:
        raise HTTPException(status_code=404, detail="Case not found")
    return db_case


@router.delete("/{case_id}", status_code=204)
def delete_case(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a case you own, including its stored artifacts and findings."""
    db_case = crud.get_case(db, case_id, owner_id=owner_scope(current_user))
    if not db_case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Collect the storage references BEFORE the DB rows disappear — afterwards
    # there is nothing left to tell us which objects belonged to this case.
    artifacts = crud.get_artifacts_by_case(db, case_id, owner_id=None)
    object_names = [a.file_path for a in artifacts if a.file_path]
    artifact_ids = [a.id for a in artifacts]

    # DB first: it is the authoritative record. If storage cleanup fails we are
    # left with orphaned bytes (recoverable), not with rows pointing at evidence
    # that has already been erased.
    db.delete(db_case)
    db.commit()

    # Case deletion used to remove only the DB rows, so every MinIO object and
    # every Chroma document survived indefinitely — deleted evidence that was
    # still downloadable by anyone who knew (or guessed) its object key, and an
    # unbounded storage leak.
    try:
        from forensicstack.core.minio_service import get_minio_service

        minio = get_minio_service()
        for object_name in object_names:
            minio.delete_artifact(object_name)
        # Sweep the whole prefix too, in case an upload left an object whose
        # Artifact row was never written.
        minio.delete_prefix(minio.case_prefix(case_id))
    except Exception as e:  # storage cleanup is best-effort
        logger.warning("Case %s: MinIO cleanup failed: %s", case_id, e)

    try:
        from forensicstack.core.chroma_service import get_chroma_service

        chroma = get_chroma_service()
        for artifact_id in artifact_ids:
            chroma.delete_by_artifact(artifact_id)
    except Exception as e:  # search-index cleanup is best-effort
        logger.warning("Case %s: ChromaDB cleanup failed: %s", case_id, e)

    return None
