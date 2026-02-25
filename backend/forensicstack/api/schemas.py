from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


# Case schemas
class CaseBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Case title")
    description: Optional[str] = Field(None, description="Case description")


class CaseCreate(CaseBase):
    """Schema for creating a case"""
    pass


class CaseUpdate(BaseModel):
    """Schema for updating a case"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(open|in_progress|closed)$")

class CaseResponse(CaseBase):
    """Schema for case response"""
    id: int
    case_number: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CaseListResponse(BaseModel):
    """Schema for listing cases"""
    cases: List[CaseResponse]
    total: int
    page: int
    page_size: int
