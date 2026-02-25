from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import List

from forensicstack.core.database import get_db
from forensicstack.core import crud
from forensicstack.api.schemas import (
    CaseCreate,
    CaseUpdate,
    CaseResponse,
    CaseListResponse
)

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])


@router.get("/", response_model=CaseListResponse)
async def list_cases(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Max records to return"),
    db: Session = Depends(get_db)
):
    """List all investigation cases with pagination"""
    cases = crud.get_cases(db, skip=skip, limit=limit)
    total = crud.get_cases_count(db)
    
    return {
        "cases": cases,
        "total": total,
        "page": skip // limit + 1 if limit > 0 else 1,
        "page_size": limit
    }


@router.post("/", response_model=CaseResponse, status_code=201)
async def create_case(
    case: CaseCreate,
    db: Session = Depends(get_db)
):
    """Create a new investigation case"""
    return crud.create_case(db, case)


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: int,
    db: Session = Depends(get_db)
):
    """Get case details by ID"""
    db_case = crud.get_case(db, case_id)
    if not db_case:
        raise HTTPException(status_code=404, detail="Case not found")
    return db_case


@router.put("/{case_id}", response_model=CaseResponse)
async def update_case(
    case_id: int,
    case_update: CaseUpdate,
    db: Session = Depends(get_db)
):
    """Update a case"""
    db_case = crud.update_case(db, case_id, case_update)
    if not db_case:
        raise HTTPException(status_code=404, detail="Case not found")
    return db_case


@router.delete("/{case_id}", status_code=204)
async def delete_case(
    case_id: int,
    db: Session = Depends(get_db)
):
    """Delete a case"""
    success = crud.delete_case(db, case_id)
    if not success:
        raise HTTPException(status_code=404, detail="Case not found")
    return None
