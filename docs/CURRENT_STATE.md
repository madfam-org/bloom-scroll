# Bloom Scroll Current State

**Last audited:** 2026-05-28 (production probes); 2026-07-16 remediation changes noted below  
**Scope:** repository files, local manifests/configuration, and public `almanac.solar` production HTTP surface.

This file is the evidence-backed current-state reference for the repo. Historical story docs remain useful for implementation context, but use this file plus the top-level READMEs for current commands, deployed behavior, and known drift. The detailed 2026-05-28 stabilization evidence trail is in [STABILITY_SESSION_2026-05-28.md](STABILITY_SESSION_2026-05-28.md).

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
  - Released Enclii CLI `v1.0.0-alpha.1` (`madfam-org/enclii@b763d92`) `ENCLII_PROJECT=bloom-scroll enclii --api-endpoint https://api.enclii.dev ps --env production` reported `bloom-scroll-web` and `bloom-scroll-api` running, `healthy`, `2/2`, and on `argocd-a84a3de`.
  - `ENCLII_PROJECT=bloom-scroll enclii ops apps status bloom-scroll-services --json` reported Argo health `Healthy`, sync `Synced`, operation phase `Succeeded`, revision `a84a3de0b614f1fc4fb2cc0a15fd846d490c02eb`, and digest-pinned images `api@sha256:70368afa2bd624b4ed61b12b23a7c0004f1f6befca74eb2ee6278598c9fcf84e` plus `web@sha256:05c726939e02a7a9a35ffb1d398f104a5848abd353a7e968ba4c23dc2fd4ca96`.
  - Earlier in the same audit, `ENCLII_PROJECT=bloom-scroll enclii ops apps diff bloom-scroll-services --json` reported drift count `0` before the final dependency-lock rollout; the final app status is `Synced` at `a84a3de`.
  - `ENCLII_PROJECT=bloom-scroll enclii observe health --service ... --json` reported both API and web services `healthy`.
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
  - `POST /api/v1/ingest/openalex`
  - `GET /api/v1/ingest/openalex/topics`
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
- Janua authentication verifies RS256 tokens through `JANUA_JWKS_URI` with issuer and optional audience checks. HS algorithms are still supported only when explicitly configured for legacy development.
- OpenAlex ingestion is implemented in `backend/app/ingestion/openalex.py` and exposes source identifiers, authors, abstracts, concepts, citation counts, and PDF URLs in the card payload.
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
  - API digest: `sha256:70368afa2bd624b4ed61b12b23a7c0004f1f6befca74eb2ee6278598c9fcf84e`.
  - Web digest: `sha256:05c726939e02a7a9a35ffb1d398f104a5848abd353a7e968ba4c23dc2fd4ca96`.
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

- Enclii production commands from a fresh checkout require explicit project context, for example `ENCLII_PROJECT=bloom-scroll enclii ps --env production`.
- Milvus exists in full local Compose and dependencies, but current application code uses PostgreSQL + pgvector for embeddings.

## Resolved During This Audit

- `enclii.yaml` status assertion was narrowed to check for `http://localhost:8000/api/v1` instead of any `localhost:` substring, because the compiled bundle legitimately includes localhost connection-help copy.
- `frontend/lib/services/api_config.dart` comments now describe the exact production-bundle check instead of a broad localhost grep.
- Root `docker-compose.yml` no longer references the missing `backend/Dockerfile.worker` and now maps the API container's port `8000` to host port `5200`.
- Backend tests now target current modules/endpoints; `poetry run pytest -q` passes 28 tests and `poetry run mypy . --ignore-missing-imports` is clean.
- `scripts/prod-smoke.sh` now checks web health, API health, feed completion, bundle API base, and production docs hiding; it passed against production after the `argocd-a84a3de` rollout.
- CI now validates the root Compose file and runs `flutter test`; the deploy workflow now runs production smoke checks after the shared Enclii build/publish workflow.
- The shared Enclii build/publish workflow was patched in `madfam-org/enclii@0a72ed7`, and the in-repo Enclii CI digest verifier in `madfam-org/enclii@f919192`, to authenticate to GHCR before digest-pin cosign verification of private packages. `madfam-org/enclii@b763d92` added tag-triggered CLI release artifacts, and `v1.0.0-alpha.1` was verified against Bloom production.
- Backend image dependency drift was narrowed by isolating heavy ML wheels from Poetry resolution; `backend/Dockerfile` installs `requirements-ml-linux-cpu.txt` before `poetry install`, keeps dependency installation ahead of `app/`, removes the unused `torchvision` preinstall, and uses BuildKit cache mounts for pip/Poetry.
- `backend/poetry.lock` is now committed for deterministic standard backend installs. `requirements-ml-linux-cpu.txt` pins Linux production ML wheels to CPU-only PyTorch (`torch==2.2.2+cpu`) plus `sentence-transformers==5.5.1` and `transformers==4.57.6`; `backend/tests/test_dependency_lock.py` guards that Poetry does not reintroduce torch, triton, transformers, sentence-transformers, or `nvidia-*` packages.
- Janua auth now verifies RS256 tokens through JWKS and includes tests for valid keys, unknown `kid` rejection, and explicit HS256 fallback.
- OpenAlex ingestion now has a repo-owned connector, endpoints, and tests for abstract reconstruction and malformed-work rejection.

## 2026-07-16 Remediation (Phase 0/1 of the vision-gap plan)

Changes landed in this repo on 2026-07-16 (see
`internal-devops/roadmaps/2026-07-16-bloom-scroll-vision-gap-remediation.md`
for the audit that motivated them). Production behavior updates after the
next deploy + `INGEST_API_KEY` secret rotation:

- **Write endpoints now require auth (D1).** `POST /api/v1/ingest/*` and
  `/api/v1/interactions/*` accept a Janua Bearer token or the
  `INGEST_API_KEY` service key via `X-API-Key`; unauthenticated writes 401.
  Reading another user's interaction history is 403 unless service role.
- **Feed pagination is honest (D2).** New `exclude_ids` query param; the
  server never re-serves excluded/read cards; `has_next_page` reflects
  actually-remaining unseen cards. The Flutter client sends read + on-screen
  ids and defensively dedupes.
- **Liveness decoupled from DB (D3).** New `/livez` endpoint; K8s liveness
  points there while readiness stays on `/health`. Rollouts are surge-free
  (`maxSurge: 0`) for the CPU-tight cluster; API memory limit raised to
  1536Mi to rule out OOM kills near the torch/SBERT ceiling.
- **Fabricated scores eliminated (D5).** New `score_provenance` column
  (migration 003) nulls all legacy hand-seeded bias/constructiveness values;
  `to_dict` only emits scores when provenance is set; the perspective
  overlay hides the gauges otherwise and shows "analysis not yet available".
- **Scheduled ingestion exists.** `infra/k8s/production/ingest-cronjob.yaml`
  runs daily at 05:10 UTC against the authenticated endpoints using
  `INGEST_API_KEY` from `bloom-scroll-secrets` (operator must add the key —
  see `secrets-template.yaml`).
- **Serendipity is pgvector-native.** The distance band + ideal-midpoint
  ordering run in SQL over the whole corpus; candidates are no longer capped
  at the ~50 most recent rows; already-seen cards are excluded; short pages
  top up with recent unseen cards.
- **Health freshness signal.** `/health` now reports `checks.freshness`
  (newest-card age, `stale` past 48h) informationally without flipping
  overall status — monitors should alert on it.
- **Dead config removed.** `BACKEND_CORS_ORIGINS` setting deleted
  (middleware reads `CORS_ALLOWED_ORIGINS`); unused `pymilvus` dependency
  dropped from `pyproject.toml`/lock (obsoletes Dependabot #95).

Operator follow-ups required to activate all of the above in production:

1. Add `INGEST_API_KEY` to the `bloom-scroll-secrets` K8s secret
   (`openssl rand -hex 32`) — via Enclii secrets tooling per
   MADFAM-ENCLII-FIRST doctrine.
2. Deploy (migration 003 clears legacy fabricated scores at PreSync).
3. Optionally trigger the CronJob once manually to refresh content
   immediately instead of waiting for 05:10 UTC.

## Recommended Next Work

1. Add frontend E2E and stress tests for finite-feed completion, pagination, production API-base behavior, missing metadata, image/aspect-ratio failures, and error-boundary paths.
2. Add production observability: error telemetry, uptime checks, latency/error dashboards, feed failure alerts, ingestion alerts, and browser error reporting.
3. Add load and soak tests for feed, health, and ingestion paths with larger card/vector counts.
4. Add runtime resilience work: app-level rate limiting, hot-feed caching, and explicit graceful-degradation tests (client retry/backoff already exists in `api_service.dart`).
5. Perspective Engine v1 (Phase 2 of the vision-gap plan): Selva-backed bias/constructiveness scoring at ingest with `score_provenance` set, real `/perspective/{card_id}` data, scoped blindspot + factfulness passes.
