"""Main FastAPI application entry point."""

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import router as api_router
from app.core.database import get_db
from app.core.error_handlers import register_error_handlers

# Audit 2026-04-23 H5: wildcard CORS + allow_credentials=True was a spec
# violation and a cross-tenant read risk. Drive the allowlist from env with
# a sensible default for almanac.solar production + local dev.
_DEFAULT_ORIGINS = (
    "https://almanac.solar",
    "https://app.almanac.solar",
    "https://api.almanac.solar",
    "http://localhost:3000",
    "http://localhost:5201",
)
_env_origins = os.getenv("CORS_ALLOWED_ORIGINS", "").strip()
_ALLOWED_ORIGINS = (
    [o.strip() for o in _env_origins.split(",") if o.strip()]
    if _env_origins
    else list(_DEFAULT_ORIGINS)
)

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle startup and shutdown events."""
    # Startup: Initialize database connections, load models, etc.
    logger.info("🌱 Bloom Scroll starting up...")
    logger.info(f"Environment: {app.debug and 'development' or 'production'}")
    yield
    # Shutdown: Cleanup resources
    logger.info("🌸 Bloom Scroll shutting down...")


# Audit 2026-04-23 H9: hide /docs + /openapi.json in production.
_DOCS_ENABLED = os.getenv("ENV", "development") != "production"

app = FastAPI(
    title="Bloom Scroll API",
    description="Backend service for perspective-driven content aggregation",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if _DOCS_ENABLED else None,
    redoc_url="/redoc" if _DOCS_ENABLED else None,
    openapi_url="/openapi.json" if _DOCS_ENABLED else None,
)

# Configure CORS (env-driven, per audit 2026-04-23 H5 — see top of file).
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

# Register global error handlers
register_error_handlers(app)
logger.info("✅ Global error handlers registered")

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "message": "Bloom Scroll API",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """
    Comprehensive health check endpoint.

    Checks:
    - API responsiveness
    - Database connectivity
    - Vector extension availability

    Returns:
    - 200 OK if all checks pass
    - 503 Service Unavailable if critical checks fail
    """
    from datetime import datetime
    from fastapi.responses import JSONResponse

    health = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.1.0",
        "checks": {}
    }

    # Check 1: Database connectivity
    try:
        await db.execute(text("SELECT 1"))
        health["checks"]["database"] = {"status": "ok", "message": "Connected"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health["checks"]["database"] = {"status": "error", "message": str(e)}
        health["status"] = "unhealthy"

    # Check 2: pgvector extension
    try:
        result = await db.execute(
            text("SELECT COUNT(*) FROM bloom_cards WHERE embedding IS NOT NULL")
        )
        vector_count = result.scalar()
        health["checks"]["vectors"] = {
            "status": "ok",
            "message": f"{vector_count} embeddings indexed"
        }
    except Exception as e:
        logger.warning(f"Vector health check failed: {e}")
        health["checks"]["vectors"] = {
            "status": "degraded",
            "message": "Vector search may be unavailable"
        }
        # Don't mark as unhealthy - vectors are not critical for basic operation

    # Check 3: Card count
    try:
        result = await db.execute(text("SELECT COUNT(*) FROM bloom_cards"))
        card_count = result.scalar()
        health["checks"]["cards"] = {
            "status": "ok",
            "message": f"{card_count} cards in database"
        }
    except Exception as e:
        logger.error(f"Card count check failed: {e}")
        health["checks"]["cards"] = {"status": "error", "message": str(e)}

    # Return appropriate status code
    status_code = 200 if health["status"] == "healthy" else 503
    return JSONResponse(content=health, status_code=status_code)
