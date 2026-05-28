# Bloom Scroll Local Infrastructure

Docker Compose files for local development. Last audited on 2026-05-28; see [../docs/CURRENT_STATE.md](../docs/CURRENT_STATE.md).

## Compose Files

### `docker-compose.dev.yml`

Minimal local infrastructure for running the backend on the host:

- PostgreSQL 15 + pgvector on `localhost:5432`
- Redis 7 on `localhost:6379`

```bash
docker-compose -f docker-compose.dev.yml up -d
docker-compose -f docker-compose.dev.yml ps
docker-compose -f docker-compose.dev.yml down
```

### `docker-compose.yml`

Full local stack:

- PostgreSQL 15 + pgvector on `localhost:5432`
- Redis 7 on `localhost:6379`
- etcd
- MinIO on `localhost:9000` and console on `localhost:9001`
- Milvus on `localhost:19530` and health on `localhost:9091`
- RSS-Bridge on `localhost:3000`
- FastAPI backend on `localhost:8000`
- Celery worker and beat containers

```bash
docker-compose up -d
docker-compose ps
curl http://localhost:8000/health
docker-compose down
```

Current application code uses PostgreSQL + pgvector for embeddings. Milvus is available in the full stack but is not the active vector path in backend code.

## Recommended Backend Flow

```bash
docker-compose -f docker-compose.dev.yml up -d

cd ../backend
poetry install
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Service Endpoints

| Service | Compose file | Host port | URL |
|---|---|---:|---|
| Backend API | `docker-compose.yml` | 8000 | `http://localhost:8000` |
| API docs | `docker-compose.yml` | 8000 | `http://localhost:8000/docs` |
| PostgreSQL | both | 5432 | `postgresql://postgres:postgres@localhost:5432/bloom_scroll` |
| Redis | both | 6379 | `redis://localhost:6379` |
| Milvus | full | 19530 | `localhost:19530` |
| MinIO console | full | 9001 | `http://localhost:9001` |
| RSS-Bridge | full | 3000 | `http://localhost:3000` |

## Database Management

```bash
docker-compose exec postgres psql -U postgres -d bloom_scroll
docker-compose exec postgres pg_dump -U postgres bloom_scroll > backup.sql
```

Use destructive volume removal only when you explicitly want to discard local data:

```bash
docker-compose down -v
```

## Troubleshooting

Check local service health:

```bash
docker-compose ps
curl http://localhost:8000/health
docker-compose exec postgres pg_isready -U postgres
```

Check common port conflicts:

```bash
lsof -i :8000
lsof -i :5432
lsof -i :6379
```

## Root Compose Note

The repository root `docker-compose.yml` is a lightweight compatibility stack. It maps the API to `5200`, Postgres to `5434`, and Redis to `6381`. Prefer the `infrastructure/` Compose files for documented backend development.
