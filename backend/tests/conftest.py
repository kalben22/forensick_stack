"""
ForensicStack test configuration.

Strategy:
  - Replace PostgreSQL with SQLite (in-memory) so tests run with no Docker.
  - Patch the MinIO / Redis / ChromaDB singletons with MagicMock objects so
    tests never attempt real network connections.
  - The patches are applied at module level, BEFORE the FastAPI app is imported,
    so the lifespan startup handler and every route dependency pick up the
    overrides automatically.
"""
import os
import pytest
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ── 1. Redirect the database to SQLite before any forensicstack import ────────

from sqlalchemy.pool import StaticPool
import forensicstack.core.database as _db

# In-memory SQLite with StaticPool so all connections share the same DB.
# The DB is fresh every pytest run — no UNIQUE constraint bleed-over between runs.
_test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_test_engine)

_db.engine = _test_engine
_db.SessionLocal = _TestingSessionLocal

# ── 2. Mock MinIO singleton ───────────────────────────────────────────────────

import forensicstack.core.minio_service as _minio_mod

_mock_minio = MagicMock()
_mock_minio.compute_hashes.return_value = (
    "d41d8cd98f00b204e9800998ecf8427e",   # md5 of empty bytes
    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
)
_mock_minio.build_object_name.return_value = "case-1/test_file.bin"
_mock_minio.upload_artifact.return_value = "case-1/test_file.bin"
_mock_minio.get_presigned_url.return_value = "http://localhost:9000/forensic-artifacts/case-1/test_file.bin"
_mock_minio.delete_artifact.return_value = None
_minio_mod._minio_service = _mock_minio

# ── 3. Mock Redis in jobs module ──────────────────────────────────────────────

import forensicstack.api.jobs as _jobs_mod

_mock_redis = MagicMock()
_mock_redis.lpush.return_value = 1
_mock_redis.hset.return_value = True
_mock_redis.hgetall.return_value = {"status": "queued"}
_jobs_mod.r = _mock_redis

# ── 4. Mock ChromaDB singleton ────────────────────────────────────────────────

import forensicstack.core.chroma_service as _chroma_mod

_mock_chroma = MagicMock()
_mock_chroma.search.return_value = []
_mock_chroma.get_stats.return_value = {"collection": "findings", "total_findings": 0}
_mock_chroma.add_findings.return_value = None
_mock_chroma.delete_by_artifact.return_value = None
_chroma_mod._chroma_service = _mock_chroma

# ── 5. Create SQLite tables ───────────────────────────────────────────────────

from forensicstack.core.models import Case, Artifact, Analysis  # noqa: F401 — register models
from forensicstack.core.models.user_model import User           # noqa: F401
from forensicstack.core.database import Base

Base.metadata.create_all(bind=_test_engine)

# ── 6. Override get_db FastAPI dependency ─────────────────────────────────────

from forensicstack.core.database import get_db
from forensicstack.api.main import app


def _override_get_db():
    db = _TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db

# ── 7. Shared fixtures ────────────────────────────────────────────────────────

from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client():
    """FastAPI TestClient backed by SQLite + mocked external services."""
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture(scope="session")
def auth_headers(client):
    """Register a test user and return its Bearer headers."""
    client.post(
        "/auth/register",
        json={"username": "testanalyst", "password": "TestPass123!"},
    )
    resp = client.post(
        "/auth/login",
        json={"username": "testanalyst", "password": "TestPass123!"},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def test_case(client, auth_headers):
    """Create a test case and return its response dict."""
    resp = client.post(
        "/api/v1/cases/",
        json={"title": "Test Case Alpha", "description": "Automated test case"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, f"Case creation failed: {resp.text}"
    return resp.json()
