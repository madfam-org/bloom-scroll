# Bloom Scroll Current State

**Last audited:** 2026-05-28  
**Scope:** repository files, local manifests/configuration, and public `almanac.solar` production HTTP surface.

This file is the evidence-backed current-state reference for the repo. Historical story docs remain useful for implementation context, but use this file plus the top-level READMEs for current commands, deployed behavior, and known drift.

## Evidence Collected

- Repo inventory: `rg --files` found FastAPI backend, Flutter frontend, Kubernetes production manifests under `infra/k8s/production`, local Compose files under `infrastructure/`, and root Compose compatibility config.
- Backend implementation: `backend/app/main.py`, `backend/app/api/routes.py`, `backend/app/api/ingestion.py`, `backend/app/api/interactions.py`, `backend/app/core/config.py`, `backend/app/core/database.py`.
- Frontend implementation: `frontend/lib/main.dart`, `frontend/lib/services/api_config.dart`, `frontend/lib/providers/feed_controller.dart`, `frontend/lib/screens/feed_screen.dart`, `frontend/pubspec.yaml`, `frontend/Dockerfile`.
- Production manifests: `infra/k8s/production/*`, `infra/argocd/config.json`, `enclii.yaml`.
- Public prod probes on 2026-05-28:
  - `https://almanac.solar` returned HTTP 200 with Flutter web shell.
  - `https://api.almanac.solar/health` returned HTTP 200 and `{"status":"healthy"}` with database OK, 8 embeddings, and 8 cards.
  - `https://api.almanac.solar/openapi.json` and `https://api.almanac.solar/docs` are no longer public after the `ENV=production` rollout.
  - `https://api.almanac.solar/api/v1/feed?limit=1` returned one card and finite pagination metadata.
  - `https://api.almanac.solar/api/v1/feed?read_count=20` returned the completion object, `"The Garden is Watered."`.
  - `https://api.almanac.solar/api/v1/ingest/datasets` returned 3 OWID datasets.
  - `https://almanac.solar/main.dart.js` contains `https://api.almanac.solar/api/v1`, proving the API base URL is baked correctly. It also contains `localhost:8000` in connection-help text, so any status check that asserts no `localhost:` substring will false-positive.
- Enclii-first production observation on 2026-05-28:
  - `ENCLII_PROJECT=bloom-scroll enclii ps --env production` reported `bloom-scroll-web` and `bloom-scroll-api` running `1/1` on `argocd-db36c34`.
  - Recent Enclii logs showed repeated HTTP 200 probe responses for web `/` and API `/health`.
  - `scripts/prod-smoke.sh` passed against `https://almanac.solar` and `https://api.almanac.solar`.

## Current Implementation

### Backend

- FastAPI app version is `0.1.0`.
- Public root endpoints:
  - `GET /`
  - `GET /health`
- API router is mounted under `/api/v1`.
- Current API endpoints observed in code and production OpenAPI:
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
- `DAILY_LIMIT = 20` is enforced in `backend/app/api/routes.py`.
- Feed defaults are `page=1`, `read_count=0`, `limit=10`, with `limit <= 20`.
- Health checks database connectivity, vector count, and card count.
- OpenAPI docs are gated in code when `ENV`, `ENVIRONMENT`, or `PYTHON_ENV` is production-like. Production manifests now set both `ENV=production` and `ENVIRONMENT=production`.
- CORS allowlist is controlled in `backend/app/main.py` by `CORS_ALLOWED_ORIGINS`. The `BACKEND_CORS_ORIGINS` setting in `backend/app/core/config.py` is currently not what the running middleware reads.
- Database URL normalization accepts `postgres://`, `postgresql://`, `postgresql+psycopg2://`, and `postgresql+psycopg://`, converting them to `postgresql+asyncpg://`.
- Sentence-BERT embeddings are implemented via `backend/app/analysis/processor.py`.
- Bias detection is still a placeholder returning `None`.
- Celery is scaffolded, but `ingest_owid_all_task` returns `{"status": "not_implemented"}`.

### Frontend

- Flutter app starts in `frontend/lib/main.dart` with `ProviderScope`, `ErrorBoundary`, `MaterialApp`, and `FeedScreen`.
- State management is Riverpod (`StateNotifierProvider`), not BLoC.
- Feed UI uses `CustomScrollView(reverse: true)` with `SliverMasonryGrid.count`.
- Cards implemented:
  - `OwidCard` with `fl_chart`.
  - `AestheticCard` with `CachedNetworkImage`, `Hero`, and an in-file full-screen image view.
  - `FlippableCard` / perspective overlay widgets.
  - `CompletionWidget`.
- API base URL is compile-time configured through `String.fromEnvironment('API_BASE_URL')`.
- `frontend/Dockerfile` defaults production web builds to `API_BASE_URL=https://api.almanac.solar`.
- Production bundle currently uses `https://api.almanac.solar/api/v1`; observed `localhost:8000` strings are connection-help copy, not the active API base.
- `frontend/test/` now covers model parsing, API configuration defaults, and daily read-state storage. CI runs `flutter test`.

### Local Development

There are three local stack entrypoints, and they are not interchangeable:

- `infrastructure/docker-compose.dev.yml`: Postgres + Redis only, intended for host-run backend.
- `infrastructure/docker-compose.yml`: full local stack with Postgres, Redis, Milvus, MinIO, RSS-Bridge, FastAPI backend on `8000`, and Celery worker/beat.
- Root `docker-compose.yml`: lightweight compatibility stack mapping API to `5200`, Postgres to `5434`, and Redis to `6381`. Prefer `infrastructure/` for documented local development.

Recommended backend dev path:

```bash
cd infrastructure
docker-compose -f docker-compose.dev.yml up -d

cd ../backend
poetry install
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Recommended Flutter web dev path:

```bash
cd frontend
flutter pub get
flutter run -d chrome --dart-define=API_BASE_URL=http://localhost:8000
```

### Production

- `enclii.yaml` declares domains `almanac.solar`, `www.almanac.solar`, and `api.almanac.solar`.
- `infra/argocd/config.json` points ArgoCD at `infra/k8s/production` on `main`.
- Kustomize pins image digests for `ghcr.io/madfam-org/bloom-scroll/api` and `ghcr.io/madfam-org/bloom-scroll/web`.
- API deployment:
  - Kubernetes deployment `bloom-scroll-api`.
  - 2 replicas.
  - Container port `8000`.
  - Probes use `/health`.
- Web deployment:
  - Kubernetes deployment `bloom-scroll-web`.
  - 2 replicas.
  - Container port `8080`.
  - Probes use `/`.
- Services are ClusterIP with service port `80` targeting API `8000` and web `8080`.
- Public production health on 2026-05-28 reported:
  - database connected
  - 8 embeddings indexed
  - 8 cards in database

## Known Gaps

- Enclii `ps` reports service health as `unknown` even while logs and public smoke checks show healthy 200 responses; the status adapter should expose probe health more clearly.
- Enclii production commands from a fresh checkout require explicit project context, for example `ENCLII_PROJECT=bloom-scroll enclii ps --env production`.
- Production contains at least one `OPENALEX` card, but this repo currently has no OpenAlex ingestion module; it is seeded or ingested outside the implemented local connectors.
- Janua/JWKS auth is described in ecosystem guidance, but local code verifies HS256 with `JANUA_JWT_SECRET`; RS256 JWKS verification is not implemented in this repo.
- Milvus exists in full local Compose and dependencies, but current application code uses PostgreSQL + pgvector for embeddings.

## Resolved During This Audit

- `enclii.yaml` status assertion was narrowed to check for `http://localhost:8000/api/v1` instead of any `localhost:` substring, because the compiled bundle legitimately includes localhost connection-help copy.
- `frontend/lib/services/api_config.dart` comments now describe the exact production-bundle check instead of a broad localhost grep.
- Root `docker-compose.yml` no longer references the missing `backend/Dockerfile.worker` and now maps the API container's port `8000` to host port `5200`.
- Backend tests now target current modules/endpoints; `poetry run pytest` passes 20 tests and `poetry run mypy . --ignore-missing-imports` is clean.
- `scripts/prod-smoke.sh` now checks web health, API health, feed completion, bundle API base, and production docs hiding; it passed against production after the `argocd-db36c34` rollout.
- CI now validates the root Compose file and runs `flutter test`; the deploy workflow now runs production smoke checks after the shared Enclii build/publish workflow.
