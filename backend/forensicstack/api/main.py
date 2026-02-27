from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer

from forensicstack.api.routes import cases, analysis, auth, artifacts, jobs, search


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle handler."""
    print("[ForensicStack] API starting...")

    from forensicstack.core.database import engine, test_connection
    # Import all models so SQLAlchemy registers them on Base.metadata
    from forensicstack.core.models import Case, Artifact, Analysis  # noqa: F401
    from forensicstack.core.models.user_model import User           # noqa: F401
    from forensicstack.core.database import Base

    Base.metadata.create_all(bind=engine)

    if test_connection():
        print("[ForensicStack] Database connected - tables ready")
    else:
        print("[ForensicStack] WARNING: Database connection failed")

    yield

    print("[ForensicStack] API shutting down...")


# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="ForensicStack API",
    description=(
        "All-in-One DFIR Investigation Platform\n\n"
        "**Auth:** Register at `/auth/register`, login at `/auth/login`, "
        "then click the 🔒 Authorize button above and paste your `access_token`."
    ),
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────

app.include_router(auth.router)          # /auth/*
app.include_router(cases.router)         # /api/v1/cases/*
app.include_router(artifacts.router)     # /api/v1/cases/{id}/artifacts/*
app.include_router(analysis.router)      # /api/v1/analysis/*
app.include_router(jobs.router)          # /api/v1/jobs/*
app.include_router(search.router)        # /api/v1/search/*


# ── Public endpoints ───────────────────────────────────────────────────────────

@app.get("/", tags=["root"])
async def root():
    return {
        "message": "Welcome to ForensicStack API",
        "version": "0.2.0",
        "status": "running",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "docs": "/docs",
        "endpoints": {
            "auth":      "/auth",
            "cases":     "/api/v1/cases",
            "artifacts": "/api/v1/cases/{case_id}/artifacts",
            "analysis":  "/api/v1/analysis",
            "jobs":      "/api/v1/jobs",
            "search":    "/api/v1/search",
            "health":    "/health",
        },
    }


@app.get("/health", tags=["root"])
async def health_check():
    from forensicstack.core.database import test_connection
    db_ok = test_connection()
    return {
        "status": "healthy" if db_ok else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "api":      "running",
            "database": "connected" if db_ok else "unavailable",
        },
    }
