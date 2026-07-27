import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from forensicstack.api.schemas import CaseCreate, CaseUpdate
from forensicstack.core.models import Analysis, Artifact, Case


def generate_case_number() -> str:
    """Generate a unique case number (date + 6-char hex suffix)."""
    now = datetime.now(timezone.utc)
    suffix = uuid.uuid4().hex[:6].upper()
    return f"CASE-{now.year}-{now.month:02d}{now.day:02d}-{suffix}"


# ===== CASES =====
#
# Every read/write below accepts `owner_id`. Passing an int scopes the query to
# that user's rows; passing None means "no ownership filter" and is reserved for
# admins (see auth.require_admin) and for background workers that run outside a
# request. Filtering in the query — rather than fetching then comparing — means
# a forgotten check cannot leak another investigator's case, and the caller
# simply gets "not found".

def create_case(db: Session, case: CaseCreate, owner_id: int) -> Case:
    """Create a new case owned by `owner_id`."""
    db_case = Case(
        case_number=generate_case_number(),
        title=case.title,
        description=case.description,
        status="open",
        owner_id=owner_id,
    )
    db.add(db_case)
    db.commit()
    db.refresh(db_case)
    return db_case


def get_case(db: Session, case_id: int, owner_id: Optional[int] = None) -> Optional[Case]:
    """Get a case by ID, restricted to `owner_id` unless it is None."""
    query = db.query(Case).filter(Case.id == case_id)
    if owner_id is not None:
        query = query.filter(Case.owner_id == owner_id)
    return query.first()


def get_case_by_number(
    db: Session, case_number: str, owner_id: Optional[int] = None
) -> Optional[Case]:
    """Get a case by case number, restricted to `owner_id` unless it is None."""
    query = db.query(Case).filter(Case.case_number == case_number)
    if owner_id is not None:
        query = query.filter(Case.owner_id == owner_id)
    return query.first()


def get_cases(
    db: Session, skip: int = 0, limit: int = 100, owner_id: Optional[int] = None
) -> List[Case]:
    """List cases with pagination, restricted to `owner_id` unless it is None."""
    query = db.query(Case)
    if owner_id is not None:
        query = query.filter(Case.owner_id == owner_id)
    return query.order_by(Case.id).offset(skip).limit(limit).all()


def get_cases_count(db: Session, owner_id: Optional[int] = None) -> int:
    """Count cases, restricted to `owner_id` unless it is None."""
    query = db.query(Case)
    if owner_id is not None:
        query = query.filter(Case.owner_id == owner_id)
    return query.count()


def update_case(
    db: Session, case_id: int, case_update: CaseUpdate, owner_id: Optional[int] = None
) -> Optional[Case]:
    """Update a case the caller owns. Returns None if absent or not owned."""
    db_case = get_case(db, case_id, owner_id=owner_id)
    if not db_case:
        return None

    update_data = case_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        # owner_id is not a client-settable field: allowing it would let a user
        # hand their case to someone else (or steal one) via a PATCH body.
        if key in {"id", "owner_id", "case_number"}:
            continue
        setattr(db_case, key, value)

    db_case.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(db_case)
    return db_case


def delete_case(db: Session, case_id: int, owner_id: Optional[int] = None) -> bool:
    """Delete a case the caller owns. Returns False if absent or not owned."""
    db_case = get_case(db, case_id, owner_id=owner_id)
    if not db_case:
        return False

    db.delete(db_case)
    db.commit()
    return True


# ===== ARTIFACTS =====
#
# Artifacts have no owner column of their own — ownership is derived from the
# parent case, so every lookup joins Case and filters on Case.owner_id.

def create_artifact(db: Session, artifact_data: dict) -> Artifact:
    """Create a new artifact. Callers must have verified case ownership first."""
    db_artifact = Artifact(**artifact_data)
    db.add(db_artifact)
    db.commit()
    db.refresh(db_artifact)
    return db_artifact


def get_artifact(
    db: Session, artifact_id: int, owner_id: Optional[int] = None
) -> Optional[Artifact]:
    """Get an artifact by ID, restricted to the owner of its case."""
    query = db.query(Artifact).filter(Artifact.id == artifact_id)
    if owner_id is not None:
        query = query.join(Case, Artifact.case_id == Case.id).filter(
            Case.owner_id == owner_id
        )
    return query.first()


def get_case_artifact(
    db: Session, case_id: int, artifact_id: int, owner_id: Optional[int] = None
) -> Optional[Artifact]:
    """
    Get an artifact that belongs to `case_id`, restricted to the case owner.

    Checking case_id in the query closes the hole where /cases/1/artifacts/99
    returned artifact 99 even though it belonged to a different case.
    """
    query = db.query(Artifact).filter(
        Artifact.id == artifact_id, Artifact.case_id == case_id
    )
    if owner_id is not None:
        query = query.join(Case, Artifact.case_id == Case.id).filter(
            Case.owner_id == owner_id
        )
    return query.first()


def get_artifacts_by_case(
    db: Session, case_id: int, owner_id: Optional[int] = None
) -> List[Artifact]:
    """List a case's artifacts, restricted to the case owner."""
    query = db.query(Artifact).filter(Artifact.case_id == case_id)
    if owner_id is not None:
        query = query.join(Case, Artifact.case_id == Case.id).filter(
            Case.owner_id == owner_id
        )
    return query.order_by(Artifact.id).all()


def count_artifacts_sharing_path(
    db: Session, file_path: str, exclude_artifact_id: int
) -> int:
    """
    How many *other* artifact rows point at the same MinIO object.

    Object keys are content-addressed, so two identical uploads legitimately
    share one object. Deleting one row must not remove bytes the other row still
    references — that would leave a live artifact whose evidence has vanished.
    """
    return (
        db.query(Artifact)
        .filter(Artifact.file_path == file_path, Artifact.id != exclude_artifact_id)
        .count()
    )


def get_artifact_by_case_and_hash(
    db: Session, case_id: int, sha256: str
) -> Optional[Artifact]:
    """Find an already-uploaded artifact with identical content in this case."""
    return (
        db.query(Artifact)
        .filter(Artifact.case_id == case_id, Artifact.file_hash_sha256 == sha256)
        .first()
    )


# ===== ANALYSES =====

def create_analysis(db: Session, analysis_data: dict) -> Analysis:
    """Create a new analysis record"""
    db_analysis = Analysis(**analysis_data)
    db.add(db_analysis)
    db.commit()
    db.refresh(db_analysis)
    return db_analysis


def get_analysis(db: Session, analysis_id: int) -> Optional[Analysis]:
    """Get analysis by ID"""
    return db.query(Analysis).filter(Analysis.id == analysis_id).first()


def get_analyses_by_artifact(db: Session, artifact_id: int) -> List[Analysis]:
    """Get all analyses for an artifact"""
    return db.query(Analysis).filter(Analysis.artifact_id == artifact_id).all()
