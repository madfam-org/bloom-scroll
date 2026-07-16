"""Main FastAPI application entry point."""

import logging
import os
import time
from collections import defaultdict, deque
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import router as api_router
from app.core.config import settings
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


# Last startup-migration failure, surfaced via /health checks.migrations so
# schema drift is observable from outside the cluster (the 2026-07-16 feed
# outage was undiagnosable externally: pods logged the failure, nothing
# exposed it).
_STARTUP_MIGRATION_ERROR: str | None = None


def _alembic_config() -> Any:
    from pathlib import Path

    from alembic.config import Config as AlembicConfig

    ini_path = Path(__file__).resolve().parents[1] / "alembic.ini"
    return AlembicConfig(str(ini_path))


def _run_migrations() -> None:
    """Apply any pending alembic migrations (sync; run via to_thread)."""
    from alembic import command

    command.upgrade(_alembic_config(), "head")


def _alembic_head() -> str | None:
    """The newest migration revision shipped in this image."""
    from alembic.script import ScriptDirectory

    return ScriptDirectory.from_config(_alembic_config()).get_current_head()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle startup and shutdown events."""
    # Startup: Initialize database connections, load models, etc.
    logger.info("🌱 Bloom Scroll starting up...")
    logger.info(f"Environment: {app.debug and 'development' or 'production'}")

    # Safety net for schema drift: the db-init PreSync job silently
    # swallowed a failed `alembic upgrade head` for months (no set -e +
    # async URL passed to sync alembic), which left migration 003
    # unapplied and 503'd every ORM query in production on 2026-07-16.
    # Non-fatal: a transient DB blip at boot must not crash-loop pods.
    import asyncio

    global _STARTUP_MIGRATION_ERROR
    try:
        await asyncio.to_thread(_run_migrations)
        _STARTUP_MIGRATION_ERROR = None
        logger.info("✅ Database schema is at alembic head")
    except Exception as e:
        _STARTUP_MIGRATION_ERROR = f"{type(e).__name__}: {e}"
        logger.exception(
            "❌ Startup migration failed — continuing, but the schema may be behind"
        )

    yield
    # Shutdown: Cleanup resources
    logger.info("🌸 Bloom Scroll shutting down...")


def _is_production_env() -> bool:
    """Return whether the current runtime should expose production behavior."""
    return any(
        os.getenv(name, "").strip().lower() in {"production", "prod"}
        for name in ("ENV", "ENVIRONMENT", "PYTHON_ENV")
    )


# Audit 2026-04-23 H9: hide /docs + /openapi.json in production.
_DOCS_ENABLED = not _is_production_env()

# Error telemetry (2026-07-16 plan, Phase 4): dormant until SENTRY_DSN is
# set in bloom-scroll-secrets. Every past incident was found by external
# probes; this is the first in-app error signal.
if settings.SENTRY_DSN:
    import sentry_sdk

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment="production" if _is_production_env() else "development",
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
    )
    logger.info("✅ Sentry error telemetry enabled")

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

# App-level rate limiting (2026-07-16 plan, Phase 4): a per-IP sliding
# window over public API GETs. In-memory per pod — a backstop against
# scraping/runaway clients, not a substitute for edge rate limiting.
_rate_buckets: dict[str, deque[float]] = defaultdict(deque)
_RATE_WINDOW_SECONDS = 60.0


@app.middleware("http")
async def rate_limit_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    limit = settings.RATE_LIMIT_PER_MINUTE
    if limit <= 0 or request.method != "GET" or not request.url.path.startswith("/api/"):
        return await call_next(request)

    # Cloudflared preserves the real client IP in CF-Connecting-IP.
    client_ip = (
        request.headers.get("CF-Connecting-IP")
        or (request.client.host if request.client else "unknown")
    )
    now = time.monotonic()
    bucket = _rate_buckets[client_ip]
    while bucket and now - bucket[0] > _RATE_WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= limit:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. The garden grows slowly."},
            headers={"Retry-After": "60"},
        )
    bucket.append(now)
    # Bound memory: drop idle buckets opportunistically.
    if len(_rate_buckets) > 10_000:
        _rate_buckets.clear()
    return await call_next(request)


# Prometheus metrics (2026-07-16 plan, Phase 4). /metrics is for the
# in-cluster scraper only: requests arriving through the Cloudflare tunnel
# carry CF headers and are refused, so the public hostname can't read it.
try:
    from prometheus_fastapi_instrumentator import Instrumentator

    Instrumentator(excluded_handlers=["/metrics", "/livez"]).instrument(app).expose(
        app, endpoint="/metrics", include_in_schema=False
    )

    @app.middleware("http")
    async def metrics_gate_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.url.path == "/metrics" and "cf-ray" in request.headers:
            return JSONResponse(status_code=404, content={"detail": "Not Found"})
        return await call_next(request)

    logger.info("✅ Prometheus /metrics exposed (in-cluster only)")
except ImportError:  # pragma: no cover - instrumentator is a hard dep in prod
    logger.warning("prometheus-fastapi-instrumentator not installed; /metrics disabled")

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


@app.get("/livez")
async def liveness_check() -> dict[str, str]:
    """
    Process-liveness endpoint for the Kubernetes liveness probe.

    Deliberately does NOT touch the database: a shared-Postgres blip must
    degrade readiness (pods leave rotation via /health) without the kubelet
    killing otherwise-healthy processes. Pointing liveness at the DB-backed
    /health was the likely cause of the 2026-05-04 restart flapping
    (14+11 restarts/47h).
    """
    return {"status": "alive"}


@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> JSONResponse:
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

    health: dict[str, Any] = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.1.0",
        "checks": {},
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
            "message": f"{vector_count} embeddings indexed",
        }
    except Exception as e:
        logger.warning(f"Vector health check failed: {e}")
        health["checks"]["vectors"] = {
            "status": "degraded",
            "message": "Vector search may be unavailable",
        }
        # Don't mark as unhealthy - vectors are not critical for basic operation

    # Check 3: Card count
    try:
        result = await db.execute(text("SELECT COUNT(*) FROM bloom_cards"))
        card_count = result.scalar()
        health["checks"]["cards"] = {
            "status": "ok",
            "message": f"{card_count} cards in database",
        }
    except Exception as e:
        logger.error(f"Card count check failed: {e}")
        health["checks"]["cards"] = {"status": "error", "message": str(e)}

    # Check 4: Content freshness (informational only — a stale corpus is a
    # product problem for monitors to alert on, not a reason to pull pods
    # out of rotation, so it never flips overall status to unhealthy).
    try:
        result = await db.execute(text("SELECT MAX(created_at) FROM bloom_cards"))
        newest = result.scalar()
        if newest is None:
            health["checks"]["freshness"] = {
                "status": "stale",
                "message": "No cards in database",
            }
        else:
            age_hours = (datetime.utcnow() - newest).total_seconds() / 3600
            health["checks"]["freshness"] = {
                "status": "ok" if age_hours <= 48 else "stale",
                "message": f"Newest card is {age_hours:.1f}h old",
                "newest_card_at": newest.isoformat(),
            }
    except Exception as e:
        logger.warning(f"Freshness check failed: {e}")
        health["checks"]["freshness"] = {"status": "unknown", "message": str(e)}

    # Check 5: schema state. The 2026-07-16 outage (unapplied migration ->
    # every ORM query 503s) was invisible: /health stayed green because it
    # only uses raw SQL. Report DB revision vs the image's alembic head so
    # monitors catch schema drift. Informational: does not flip overall
    # status (restarting pods cannot fix a behind schema).
    try:
        result = await db.execute(text("SELECT version_num FROM alembic_version"))
        db_revision = result.scalar()
        head_revision = _alembic_head()
        schema_check: dict[str, Any] = {
            "status": "ok" if db_revision == head_revision else "behind",
            "db_revision": db_revision,
            "head_revision": head_revision,
        }
        if _STARTUP_MIGRATION_ERROR:
            schema_check["status"] = "error"
            schema_check["startup_migration_error"] = _STARTUP_MIGRATION_ERROR
        health["checks"]["migrations"] = schema_check
    except Exception as e:
        logger.warning(f"Migration state check failed: {e}")
        health["checks"]["migrations"] = {"status": "unknown", "message": str(e)}

    # Return appropriate status code
    status_code = 200 if health["status"] == "healthy" else 503
    return JSONResponse(content=health, status_code=status_code)
