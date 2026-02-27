from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from typing import Optional, List, Dict, Any


# ============================================================
# CASE SCHEMAS
# ============================================================

class CaseBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class CaseCreate(CaseBase):
    pass


class CaseUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(open|in_progress|closed)$")


class CaseResponse(CaseBase):
    id: int
    case_number: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CaseListResponse(BaseModel):
    cases: List[CaseResponse]
    total: int
    page: int
    page_size: int


# ============================================================
# AUTH SCHEMAS
# ============================================================

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    email: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str]
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int          # seconds
    username: str
    role: str


# ============================================================
# ARTIFACT SCHEMAS
# ============================================================

class ArtifactResponse(BaseModel):
    id: int
    case_id: int
    filename: str
    artifact_type: Optional[str]
    file_path: str
    file_size: Optional[int]
    file_hash_md5: Optional[str]
    file_hash_sha256: Optional[str]
    uploaded_at: datetime
    download_url: Optional[str] = None

    class Config:
        from_attributes = True


class ArtifactListResponse(BaseModel):
    artifacts: List[ArtifactResponse]
    total: int


# ============================================================
# JOB SCHEMAS
# ============================================================

class JobSubmitRequest(BaseModel):
    tool: str = Field(..., description="Tool name from PLUGIN_REGISTRY (ileapp, aleapp, exiftool, volatility)")
    artifact_id: int = Field(..., description="ID of the artifact to analyse")
    input_type: Optional[str] = Field(None, description="Optional input type hint (fs, tar, file…)")


class JobStatusResponse(BaseModel):
    job_id: str
    status: str                        # queued | running | completed | failed | not_found
    findings: Optional[List[Dict[str, Any]]] = None
    output_prefix: Optional[str] = None
    error: Optional[str] = None


# ============================================================
# SEARCH SCHEMAS
# ============================================================

class SemanticSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language search query")
    top_k: int = Field(10, ge=1, le=100, description="Number of results to return")
    case_id: Optional[int] = Field(None, description="Filter results to a specific case")
    tool: Optional[str] = Field(None, description="Filter results to a specific tool")


class SearchResult(BaseModel):
    score: float
    tool: str
    artifact_type: str
    source: Optional[str]
    timestamp: Optional[str]
    artifact_id: int
    case_id: int
    confidence: float
    data: Dict[str, Any]


class SemanticSearchResponse(BaseModel):
    query: str
    total: int
    results: List[SearchResult]
