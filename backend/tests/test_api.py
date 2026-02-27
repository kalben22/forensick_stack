"""
API integration tests — full request/response cycle via TestClient.

External services (PostgreSQL, Redis, MinIO, ChromaDB) are replaced by
SQLite + MagicMock in conftest.py, so these tests run without any Docker.
"""
import io
import pytest


# ═══════════════════════════════════════════════════════════
# ROOT / HEALTH
# ═══════════════════════════════════════════════════════════

class TestRoot:
    def test_root_returns_welcome(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "running"
        assert "version" in body

    def test_health_check(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["services"]["api"] == "running"


# ═══════════════════════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════════════════════

class TestAuth:
    def test_register_success(self, client):
        resp = client.post(
            "/auth/register",
            json={"username": "newuser", "password": "NewPass123!"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["username"] == "newuser"
        assert body["role"] == "analyst"
        assert "hashed_password" not in body

    def test_register_duplicate_username(self, client):
        client.post("/auth/register", json={"username": "dupuser", "password": "Pass1234!"})
        resp = client.post("/auth/register", json={"username": "dupuser", "password": "Pass1234!"})
        assert resp.status_code == 409

    def test_login_success(self, client):
        client.post("/auth/register", json={"username": "loginuser", "password": "Login123!"})
        resp = client.post("/auth/login", json={"username": "loginuser", "password": "Login123!"})
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert body["username"] == "loginuser"

    def test_login_wrong_password(self, client):
        client.post("/auth/register", json={"username": "wrongpw", "password": "Correct1!"})
        resp = client.post("/auth/login", json={"username": "wrongpw", "password": "Wrong1234!"})
        assert resp.status_code == 401

    def test_login_unknown_user(self, client):
        resp = client.post("/auth/login", json={"username": "nobody", "password": "Pass1234!"})
        assert resp.status_code == 401

    def test_me_authenticated(self, client, auth_headers):
        resp = client.get("/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["username"] == "testanalyst"

    def test_me_unauthenticated(self, client):
        resp = client.get("/auth/me")
        assert resp.status_code == 403   # HTTPBearer returns 403 when no credentials

    def test_me_invalid_token(self, client):
        resp = client.get("/auth/me", headers={"Authorization": "Bearer invalid.jwt.token"})
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════
# CASES
# ═══════════════════════════════════════════════════════════

class TestCases:
    def test_create_case(self, client, auth_headers):
        resp = client.post(
            "/api/v1/cases/",
            json={"title": "My First Case", "description": "Test"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["title"] == "My First Case"
        assert body["status"] == "open"
        assert body["case_number"].startswith("CASE-")

    def test_list_cases(self, client, auth_headers):
        resp = client.get("/api/v1/cases/", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "cases" in body
        assert isinstance(body["cases"], list)

    def test_get_case(self, client, auth_headers, test_case):
        case_id = test_case["id"]
        resp = client.get(f"/api/v1/cases/{case_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == case_id

    def test_get_case_not_found(self, client, auth_headers):
        resp = client.get("/api/v1/cases/999999", headers=auth_headers)
        assert resp.status_code == 404

    def test_update_case(self, client, auth_headers, test_case):
        case_id = test_case["id"]
        resp = client.patch(
            f"/api/v1/cases/{case_id}",
            json={"status": "in_progress"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "in_progress"

    def test_cases_require_auth(self, client):
        resp = client.get("/api/v1/cases/")
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════
# ARTIFACTS
# ═══════════════════════════════════════════════════════════

class TestArtifacts:
    def test_upload_artifact(self, client, auth_headers, test_case):
        case_id = test_case["id"]
        file_content = b"MZ" + b"\x00" * 100   # fake PE header bytes
        resp = client.post(
            f"/api/v1/cases/{case_id}/artifacts/",
            files={"file": ("test_binary.bin", io.BytesIO(file_content), "application/octet-stream")},
            data={"artifact_type": "malware_sample"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["case_id"] == case_id
        assert body["filename"] == "test_binary.bin"
        assert body["artifact_type"] == "malware_sample"
        assert body["file_hash_md5"] is not None
        assert body["file_hash_sha256"] is not None

    def test_upload_invalid_type(self, client, auth_headers, test_case):
        case_id = test_case["id"]
        resp = client.post(
            f"/api/v1/cases/{case_id}/artifacts/",
            files={"file": ("x.bin", io.BytesIO(b"data"), "application/octet-stream")},
            data={"artifact_type": "invalid_type"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_upload_to_nonexistent_case(self, client, auth_headers):
        resp = client.post(
            "/api/v1/cases/999999/artifacts/",
            files={"file": ("x.bin", io.BytesIO(b"data"), "application/octet-stream")},
            data={"artifact_type": "other"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_list_artifacts(self, client, auth_headers, test_case):
        case_id = test_case["id"]
        resp = client.get(f"/api/v1/cases/{case_id}/artifacts/", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "artifacts" in body
        assert isinstance(body["artifacts"], list)

    def test_get_artifact(self, client, auth_headers, test_case):
        case_id = test_case["id"]
        # Upload first
        upload = client.post(
            f"/api/v1/cases/{case_id}/artifacts/",
            files={"file": ("get_test.bin", io.BytesIO(b"hello"), "application/octet-stream")},
            data={"artifact_type": "other"},
            headers=auth_headers,
        )
        artifact_id = upload.json()["id"]

        resp = client.get(
            f"/api/v1/cases/{case_id}/artifacts/{artifact_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == artifact_id

    def test_delete_artifact(self, client, auth_headers, test_case):
        case_id = test_case["id"]
        upload = client.post(
            f"/api/v1/cases/{case_id}/artifacts/",
            files={"file": ("del_test.bin", io.BytesIO(b"bye"), "application/octet-stream")},
            data={"artifact_type": "other"},
            headers=auth_headers,
        )
        artifact_id = upload.json()["id"]

        resp = client.delete(
            f"/api/v1/cases/{case_id}/artifacts/{artifact_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 204


# ═══════════════════════════════════════════════════════════
# JOBS
# ═══════════════════════════════════════════════════════════

class TestJobs:
    def test_list_tools(self, client, auth_headers):
        resp = client.get("/api/v1/jobs/tools", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "tools" in body
        tool_names = [t["name"] for t in body["tools"]]
        assert "exiftool" in tool_names
        assert "volatility" in tool_names
        assert "ileapp" in tool_names
        assert "aleapp" in tool_names

    def test_submit_job(self, client, auth_headers, test_case):
        case_id = test_case["id"]
        # Upload an artifact first
        upload = client.post(
            f"/api/v1/cases/{case_id}/artifacts/",
            files={"file": ("job_test.jpg", io.BytesIO(b"\xff\xd8\xff" + b"\x00" * 50), "image/jpeg")},
            data={"artifact_type": "document"},
            headers=auth_headers,
        )
        artifact_id = upload.json()["id"]

        resp = client.post(
            "/api/v1/jobs/submit",
            json={"tool": "exiftool", "artifact_id": artifact_id},
            headers=auth_headers,
        )
        assert resp.status_code == 202
        body = resp.json()
        assert "job_id" in body
        assert body["status"] == "queued"

    def test_submit_unknown_tool(self, client, auth_headers, test_case):
        resp = client.post(
            "/api/v1/jobs/submit",
            json={"tool": "nonexistent_tool", "artifact_id": 1},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_submit_nonexistent_artifact(self, client, auth_headers):
        resp = client.post(
            "/api/v1/jobs/submit",
            json={"tool": "exiftool", "artifact_id": 999999},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_job_status(self, client, auth_headers):
        resp = client.get("/api/v1/jobs/fake-job-id-123", headers=auth_headers)
        assert resp.status_code == 200
        # Redis mock returns {"status": "queued"} for any key
        assert "status" in resp.json()


# ═══════════════════════════════════════════════════════════
# SEMANTIC SEARCH
# ═══════════════════════════════════════════════════════════

class TestSearch:
    def test_semantic_search_empty(self, client, auth_headers):
        resp = client.post(
            "/api/v1/search/semantic",
            json={"query": "suspicious process injection", "top_k": 5},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["query"] == "suspicious process injection"
        assert body["total"] == 0
        assert body["results"] == []

    def test_semantic_search_with_filters(self, client, auth_headers):
        resp = client.post(
            "/api/v1/search/semantic",
            json={"query": "malware", "top_k": 10, "case_id": 1, "tool": "volatility"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_semantic_search_invalid_query(self, client, auth_headers):
        resp = client.post(
            "/api/v1/search/semantic",
            json={"query": "", "top_k": 5},
            headers=auth_headers,
        )
        assert resp.status_code == 422   # Pydantic min_length=1 validation

    def test_search_stats(self, client, auth_headers):
        resp = client.get("/api/v1/search/stats", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "total_findings" in body
