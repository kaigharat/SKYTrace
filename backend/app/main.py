"""Main FastAPI application entrypoint."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.api.endpoints import router as endpoints_router
from backend.ml.inference.engine import get_inference_engine
from backend.app.services.repo_service import get_repo_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Warm up ML inference engine and repository intelligence service
    print("[SkyTrace Backend] Initializing ML Inference Engine & Repository Service...")
    engine = get_inference_engine()
    service = get_repo_service()
    print(f"[SkyTrace Backend] Pre-loaded {len(service.repositories)} repositories and ML Baseline model.")
    yield
    print("[SkyTrace Backend] Shutting down.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Unified backend API connecting the Next.js frontend with the SkyTrace ML risk inference models.",
    lifespan=lifespan,
)

# CORS middleware for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API endpoints under /api prefix
app.include_router(endpoints_router, prefix=settings.API_PREFIX)


@app.get("/health", tags=["System"])
def health_check_root():
    """Root-level health check for load-balancer and Docker probes."""
    return {"status": "healthy", "service": "SkyTrace Repository Intelligence API", "ml_ready": True}


@app.get("/")
def root():
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "docs_url": "/docs",
    }
