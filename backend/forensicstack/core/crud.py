import uuid
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from forensicstack.core.models import Case, Artifact, Analysis
from forensicstack.api.schemas import CaseCreate, CaseUpdate

def generate_case_number() -> str:
    """Generate a unique case number (date + 6-char hex suffix)."""
    now = datetime.utcnow()
    suffix = uuid.uuid4().hex[:6].upper()
    return f"CASE-{now.year}-{now.month:02d}{now.day:02d}-{suffix}"

# ===== CASES =====cl
def create_case(db: Session, case: CaseCreate) -> Case:
    """Create a new case"""
    db_case = Case(
        case_number=generate_case_number(),
        title=case.title,
        description=case.description,
        status="open"
    )
    db.add(db_case)
    db.commit()
    db.refresh(db_case)
    return db_case


def get_case(db: Session, case_id: int) -> Optional[Case]:
    """Get case by ID"""
    return db.query(Case).filter(Case.id == case_id).first()


def get_case_by_number(db: Session, case_number: str) -> Optional[Case]:
    """Get case by case number"""
    return db.query(Case).filter(Case.case_number == case_number).first()


def get_cases(db: Session, skip: int = 0, limit: int = 100) -> List[Case]:
    """Get all cases with pagination"""
    return db.query(Case).offset(skip).limit(limit).all()


def get_cases_count(db: Session) -> int:
    """Get total number of cases"""
    return db.query(Case).count()


def update_case(db: Session, case_id: int, case_update: CaseUpdate) -> Optional[Case]:
    """Update a case"""
    db_case = get_case(db, case_id)
    if not db_case:
        return None
    
    update_data = case_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_case, key, value)
    
    db_case.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_case)
    return db_case


def delete_case(db: Session, case_id: int) -> bool:
    """Delete a case"""
    db_case = get_case(db, case_id)
    if not db_case:
        return False
    
    db.delete(db_case)
    db.commit()
    return True


# ===== ARTIFACTS =====

def create_artifact(db: Session, artifact_data: dict) -> Artifact:
    """Create a new artifact"""
    db_artifact = Artifact(**artifact_data)
    db.add(db_artifact)
    db.commit()
    db.refresh(db_artifact)
    return db_artifact


def get_artifact(db: Session, artifact_id: int) -> Optional[Artifact]:
    """Get artifact by ID"""
    return db.query(Artifact).filter(Artifact.id == artifact_id).first()


def get_artifacts_by_case(db: Session, case_id: int) -> List[Artifact]:
    """Get all artifacts for a case"""
    return db.query(Artifact).filter(Artifact.case_id == case_id).all()


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
