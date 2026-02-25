from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from forensicstack.api.routes import cases, analysis

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

#Import volatility routes
app.include_router(cases.router)
app.include_router(analysis.router)

@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    print("ForensicStack API starting...")
    
    from forensicstack.core.database import test_connection
    
    if test_connection():
        print("Database connected")
    else:
        print("Database connection failed")


# Import routes
from forensicstack.api.routes import cases
app.include_router(cases.router)


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


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "api": "running",
            "database": "connected"
        }
    }