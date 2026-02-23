from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])

# Pydantic schemas
class CaseCreate(BaseModel):
    title: str
    description: str | None = None

class CaseResponse(BaseModel):
    id: int
    case_number: str
    title: str
    description: str | None
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# TODO: Ajouter database dependency
# @router.get("/", response_model=List[CaseResponse])
# async def list_cases():
#     return []

@router.get("/")
async def list_cases():
    """List all investigation cases"""
    # TODO: Query database
    return {
        "cases": [],
        "total": 0,
        "message": "Database integration coming next"
    }

@router.post("/")
async def create_case(case: CaseCreate):
    """Create a new investigation case"""
    # TODO: Save to database
    return {
        "message": "Case created (mock)",
        "case": {
            "id": 1,
            "case_number": "CASE-2026-001",
            "title": case.title,
            "description": case.description,
            "status": "open"
        }
    }

@router.get("/{case_id}")
async def get_case(case_id: int):
    """Get case details"""
    # TODO: Query database
    return {"id": case_id, "message": "Case details coming soon"}