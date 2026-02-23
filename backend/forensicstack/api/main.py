from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import sys
from pathlib import Path

# Ajouter le dossier parent au path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

app = FastAPI(
    title="ForensicStack API",
    description="All-in-One DFIR Investigation Platform with AI Agents",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import et inclure les routes
from forensicstack.api.routes import cases

app.include_router(cases.router)

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to ForensicStack API",
        "version": "0.1.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "docs": "/docs",
        "endpoints": {
            "cases": "/api/v1/cases",
            "health": "/health"
        }
    }

# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "api": "running",
            "database": "configured",
            "redis": "configured",
            "celery": "configured"
        }
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting ForensicStack API...")
    print("📍 URL: http://localhost:8001")
    print("📖 Docs: http://localhost:8001/docs")
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)