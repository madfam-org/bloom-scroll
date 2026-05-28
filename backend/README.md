# Bloom Scroll Backend

FastAPI backend for Bloom Scroll / Almanac. Last audited against code and production on 2026-05-28; see [../docs/CURRENT_STATE.md](../docs/CURRENT_STATE.md).

## Current Stack

- Python 3.11+
- FastAPI + Uvicorn
- SQLAlchemy async sessions with `asyncpg`
- PostgreSQL + pgvector for card storage and embeddings
- Redis and Celery are configured; the current Celery ingestion task is scaffolded and returns `not_implemented`
- Sentence-BERT (`sentence-transformers/all-MiniLM-L6-v2`) for 384-dimensional embeddings
- PyTorch is constrained to `>=2.1,<2.3`; newer unconstrained releases currently break macOS x86_64 local installs and increase image drift risk.
- Bias detection is a placeholder in `app/analysis/processor.py`

Milvus appears in dependencies and full local Compose, but current application code stores/query embeddings through PostgreSQL + pgvector.

## Project Structure

```text
backend/
├── app/
│   ├── analysis/      # NLPProcessor for embeddings and placeholder bias scoring
│   ├── api/           # Feed, ingestion, and interaction endpoints
│   ├── core/          # Config, auth helpers, DB, error handlers
│   ├── curation/      # BloomAlgorithm serendipity logic
│   ├── ingestion/     # OWID and Are.na connectors
│   ├── models/        # SQLAlchemy models
│   ├── schemas/       # Pydantic schemas
│   ├── main.py        # FastAPI app
│   └── worker.py      # Celery scaffold
├── alembic/           # Database migrations
├── tests/             # Pytest tests
├── Dockerfile
├── pyproject.toml
└── run_dev.sh
```

## Local Development

Start Postgres and Redis:

```bash
cd ../infrastructure
docker-compose -f docker-compose.dev.yml up -d
```

Install dependencies, migrate, and run:

```bash
cd ../backend
poetry install
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

`./run_dev.sh` performs the same dependency/migration/server flow and expects local Postgres on `localhost:5432`.

## API Surface

The API router is mounted at `/api/v1`.

- `GET /health`
- `GET /api/v1/feed`
- `GET /api/v1/perspective/{card_id}` (placeholder response)
- `POST /api/v1/ingest/owid`
- `POST /api/v1/ingest/owid/all`
- `GET /api/v1/ingest/datasets`
- `POST /api/v1/ingest/aesthetics`
- `POST /api/v1/ingest/aesthetics/all`
- `GET /api/v1/ingest/aesthetics/channels`
- `POST /api/v1/interactions/track`
- `GET /api/v1/interactions/recent/{user_id}`

Local docs are available at `http://localhost:8000/docs`. Production-like environments disable `/docs`, `/redoc`, and `/openapi.json`; `scripts/prod-smoke.sh` checks that on `api.almanac.solar`.

## Configuration Notes

- `DATABASE_URL` is normalized to `postgresql+asyncpg://` in `app/core/database.py`.
- Runtime CORS middleware reads `CORS_ALLOWED_ORIGINS` in `app/main.py`.
- `BACKEND_CORS_ORIGINS` exists in settings but is not currently wired into middleware.
- Auth helpers verify HS256 tokens using `JANUA_JWT_SECRET`; RS256 JWKS verification is not implemented in this repo yet.
- Docs are disabled when `ENV`, `ENVIRONMENT`, or `PYTHON_ENV` is production-like.
- `backend/Dockerfile` pre-installs CPU-only torch in the same version range as `pyproject.toml`, copies dependency metadata before `app/`, and uses BuildKit cache mounts so app-only edits do not invalidate the heavy ML dependency layers.

## Tests

```bash
poetry run pytest
```

Current backend tests cover health, finite-feed behavior, API validation, and poison-pill ingestion paths.

Focused test command:

```bash
poetry run pytest tests/test_health.py tests/test_feeds.py tests/test_ingestion_gauntlet.py
```
