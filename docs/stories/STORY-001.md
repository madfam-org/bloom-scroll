# STORY-001: Infrastructure & OWID Ingestion

> [!IMPORTANT]
> MADFAM-ENCLII-FIRST-LEGACY-RAW v1: This document contains legacy raw infrastructure command examples.
> Routine production operations must use Enclii web, API, or CLI. Treat raw
> `kubectl`, `helm`, SSH, provider CLI/API, `docker exec`, and direct container
> access as platform bootstrap or documented break-glass only, and record any
> missing Enclii adapter gap.


**Status**: ✅ Implemented
**Epic**: The Root System
**Priority**: P0

## Overview

This story establishes the foundational infrastructure for Bloom Scroll and implements the first data ingestion pipeline for Our World in Data (OWID).

## What Was Built

### 1. Infrastructure (Docker)

- **PostgreSQL 15** with pgvector extension
- **Redis 7** for caching and Celery message broker
- **FastAPI backend** with async support
- **Alembic** for database migrations
- **Celery worker** (scaffolded for future background tasks)

### 2. Database Schema

Created `bloom_cards` table with:
- UUID primary key
- Source type classification
- JSONB data payload (polymorphic content)
- Perspective engine metadata fields
- pgvector embedding column (384 dimensions)
- Indexes for performance

See migration: `backend/alembic/versions/20251119_0100-001_initial_bloom_cards_table.py`

### 3. OWID Connector (`app/ingestion/owid.py`)

- Fetches raw CSV data from OWID GitHub repository
- Transforms data into BloomCard format
- Supports multiple datasets:
  - CO2 emissions
  - Life expectancy
  - Child mortality
- Configurable entity (country/region) and time range
- Async implementation for performance

### 4. API Endpoints

#### POST `/api/v1/ingest/owid`
Ingest a single OWID dataset

**Parameters:**
- `dataset_key`: Dataset identifier (default: "co2_emissions")
- `entity`: Country/region (default: "World")
- `years_back`: Number of years to fetch (default: 20)

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/ingest/owid?dataset_key=co2_emissions&entity=World&years_back=20"
```

#### POST `/api/v1/ingest/owid/all`
Ingest all available OWID datasets

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/ingest/owid/all"
```

#### GET `/api/v1/ingest/datasets`
List all available OWID datasets

#### GET `/api/v1/feed`
Retrieve recent BloomCards (basic implementation)

## Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# Start infrastructure
cd infrastructure
docker-compose -f docker-compose.dev.yml up -d

# Wait for services to be ready (check with docker-compose ps)

# Run migrations from host
cd ../backend
poetry install
poetry run alembic upgrade head

# Test ingestion
poetry run python test_story_001.py

# Start API server
poetry run uvicorn app.main:app --reload
```

### Option 2: Development Script

```bash
# Start infrastructure
cd infrastructure
docker-compose -f docker-compose.dev.yml up -d

# Run dev script (installs deps, runs migrations, starts server)
cd ../backend
./run_dev.sh
```

### Option 3: Full Stack

```bash
cd infrastructure
docker-compose up -d
# This starts everything including backend in container
```

## Testing the Implementation

### Automated Test
```bash
cd backend
poetry run python test_story_001.py
```

This validates:
1. ✓ Database connection works
2. ✓ OWID ingestion creates a card
3. ✓ Data payload is valid JSON

### Manual Testing

1. **Start services:**
   ```bash
   cd infrastructure
   docker-compose -f docker-compose.dev.yml up -d
   ```

2. **Check health:**
   ```bash
   curl http://localhost:8000/health
   ```

3. **List available datasets:**
   ```bash
   curl http://localhost:8000/api/v1/ingest/datasets
   ```

4. **Ingest CO2 data:**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/ingest/owid?dataset_key=co2_emissions"
   ```

5. **View API docs:**
   Open http://localhost:8000/docs in your browser

6. **Check database:**
   ```bash
   docker exec -it bloom-postgres psql -U postgres -d bloom_scroll
   ```
   ```sql
   SELECT id, source_type, title, created_at FROM bloom_cards;
   SELECT data_payload FROM bloom_cards WHERE source_type = 'OWID' LIMIT 1;
   ```

## Acceptance Criteria Status

- [x] **AC1**: Running `docker-compose up` starts all 4 containers without error
- [x] **AC2**: Triggering ingestion endpoint results in new row in `bloom_cards` table
- [x] **AC3**: Querying that row shows valid JSON structure in `data_payload`

## File Structure

```
backend/
├── alembic/
│   ├── versions/
│   │   └── 20251119_0100-001_initial_bloom_cards_table.py
│   ├── env.py
│   └── script.py.mako
├── app/
│   ├── api/
│   │   ├── ingestion.py          # NEW: Ingestion endpoints
│   │   └── routes.py              # UPDATED: Includes ingestion router
│   ├── core/
│   │   ├── config.py              # NEW: Settings management
│   │   └── database.py            # NEW: DB connection
│   ├── ingestion/
│   │   └── owid.py                # NEW: OWID connector
│   ├── models/
│   │   └── bloom_card.py          # NEW: BloomCard model
│   ├── schemas/
│   │   └── bloom_card.py          # NEW: Pydantic schemas
│   ├── main.py                    # UPDATED: App initialization
│   └── worker.py                  # NEW: Celery config
├── alembic.ini                    # NEW: Alembic config
├── test_story_001.py              # NEW: Acceptance tests
└── run_dev.sh                     # NEW: Dev startup script

infrastructure/
├── docker-compose.yml             # UPDATED: Added pgvector
├── docker-compose.dev.yml         # NEW: Minimal dev setup
└── init-scripts/
    └── 01_enable_extensions.sql   # NEW: Enable pgvector
```

## Data Payload Example

```json
{
  "chart_type": "line",
  "years": [2004, 2005, 2006, ..., 2023],
  "values": [29531.2, 30142.5, 30798.4, ..., 37152.8],
  "unit": "tonnes",
  "indicator": "CO2 emissions",
  "entity": "World"
}
```

## Next Steps

### STORY-002 (Suggested): Frontend Masonry Grid
- Create Flutter widgets to render OWID charts
- Implement upward scrolling
- Display BloomCards in masonry layout

### STORY-003 (Suggested): OpenAlex Integration
- Add science paper ingestion
- Implement abstract summarization
- Store paper metadata

### STORY-004 (Suggested): Embedding Generation
- Integrate Sentence-BERT
- Generate embeddings for existing cards
- Store in pgvector column

## Troubleshooting

### PostgreSQL connection refused
```bash
# Check if container is running
docker ps | grep bloom-postgres

# Check logs
docker logs bloom-postgres

# Verify port mapping
lsof -i :5432
```

### Migration fails
```bash
# Reset database (destructive!)
docker-compose down -v
docker-compose up -d postgres
# Wait for PostgreSQL to start
poetry run alembic upgrade head
```

### Import errors
```bash
# Reinstall dependencies
poetry install
```

### OWID data fetch fails
- Check internet connection
- Verify OWID GitHub repository is accessible
- Check dataset path in `app/ingestion/owid.py`

## Performance Notes

- OWID CSV fetching takes ~2-5 seconds per dataset
- Database insert is < 50ms
- API response time: ~3-5 seconds for first ingestion (includes HTTP fetch)
- Subsequent queries: < 100ms

## Security Considerations

- PostgreSQL uses default credentials (change in production!)
- No authentication on API endpoints (add in later stories)
- CORS is wide open (configure for production)
- Rate limiting not implemented (add in later stories)

---

**Completed**: 2025-11-19
**Next Story**: TBD (Frontend or Additional Data Sources)
