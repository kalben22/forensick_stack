"""Correlation-id middleware: every response is traceable."""


class TestRequestId:
    def test_response_carries_a_request_id(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        rid = resp.headers.get("x-request-id")
        assert rid and len(rid) >= 8

    def test_caller_supplied_id_is_echoed(self, client):
        # A caller can thread its own id through so a single action can be traced
        # across the frontend, the API and a worker.
        resp = client.get("/health", headers={"X-Request-ID": "trace-abc-123"})
        assert resp.headers.get("x-request-id") == "trace-abc-123"

    def test_overlong_id_is_truncated(self, client):
        resp = client.get("/health", headers={"X-Request-ID": "z" * 500})
        assert len(resp.headers.get("x-request-id", "")) <= 64
