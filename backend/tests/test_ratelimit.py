"""Rate limiter: window logic (unit) + endpoint enforcement (integration)."""

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from forensicstack.core.ratelimit import FixedWindowLimiter, rate_limit


class TestFixedWindow:
    def test_allows_up_to_limit_then_blocks(self):
        lim = FixedWindowLimiter(limit=3, window_seconds=60)
        # A frozen clock keeps all hits inside one window.
        results = [lim.check("ip-a", now=100.0)[0] for _ in range(5)]
        assert results == [True, True, True, False, False]

    def test_window_rolls_over(self):
        lim = FixedWindowLimiter(limit=1, window_seconds=60)
        assert lim.check("ip-a", now=0.0)[0] is True
        assert lim.check("ip-a", now=1.0)[0] is False  # same window
        assert lim.check("ip-a", now=61.0)[0] is True  # new window

    def test_keys_are_independent(self):
        lim = FixedWindowLimiter(limit=1, window_seconds=60)
        assert lim.check("ip-a", now=0.0)[0] is True
        assert lim.check("ip-b", now=0.0)[0] is True  # different client
        assert lim.check("ip-a", now=0.0)[0] is False

    def test_retry_after_is_positive_when_blocked(self):
        lim = FixedWindowLimiter(limit=1, window_seconds=60)
        lim.check("ip-a", now=0.0)
        allowed, retry = lim.check("ip-a", now=10.0)
        assert allowed is False
        assert 1 <= retry <= 60


class TestDependencyEnforcement:
    def _app(self):
        app = FastAPI()
        guard = rate_limit("probe", limit=2, window_seconds=60, enabled=True)

        @app.get("/probe", dependencies=[Depends(guard)])
        def probe():
            return {"ok": True}

        return TestClient(app)

    def test_third_call_is_429_with_retry_after(self):
        c = self._app()
        assert c.get("/probe").status_code == 200
        assert c.get("/probe").status_code == 200
        blocked = c.get("/probe")
        assert blocked.status_code == 429
        assert int(blocked.headers["retry-after"]) >= 1

    def test_disabled_never_blocks(self):
        app = FastAPI()
        guard = rate_limit("off", limit=1, window_seconds=60, enabled=False)

        @app.get("/off", dependencies=[Depends(guard)])
        def off():
            return {"ok": True}

        c = TestClient(app)
        assert all(c.get("/off").status_code == 200 for _ in range(5))
