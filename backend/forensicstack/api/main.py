from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer

import os

from forensicstack.api.routes import (
    analyze, cases, auth, artifacts, jobs, search,
)

# NOTE: `routes.analysis` (/api/v1/analysis/*) is deliberately NOT imported.
# That surface is dead: it dispatches with Celery `.delay()`, but no Celery
# worker exists in docker-compose (the `worker` service runs the Redis-stream
# consumer), its tools are absent from requirements.txt, and the tasks hand a
# MinIO object key to code that expects a local filesystem path. Every call
# returned a task_id that stayed PENDING forever.
# Worse, importing it hard-fails the whole API when celery is not installed.
# The replacement is /api/v1/analyze/*. Delete routes/analysis.py and
# core/tasks.py once you have confirmed nothing external depends on them.


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

# `allow_origins=["*"]` together with `allow_credentials=True` is an invalid
# combination that Starlette silently degrades and browsers reject for
# credentialed requests -- and it let any origin drive the API with a stolen
# token. Origins are now explicit and environment-driven.
_origins = [
    o.strip()
    for o in os.getenv(
        "CORS_ALLOW_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=600,
)

# ── Routers ────────────────────────────────────────────────────────────────────

app.include_router(auth.router)          # /auth/*
app.include_router(cases.router)         # /api/v1/cases/*
app.include_router(artifacts.router)     # /api/v1/cases/{id}/artifacts/*
app.include_router(jobs.router)          # /api/v1/jobs/*
app.include_router(analyze.router)       # /api/v1/analyze/*  (auto-triage + routing)
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
