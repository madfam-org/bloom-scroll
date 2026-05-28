# Bloom Scroll Agent Operating Guide

> [!IMPORTANT]
> MADFAM-ENCLII-FIRST-LEGACY-RAW v1: This document contains legacy raw infrastructure command examples.
> Routine production operations must use Enclii web, API, or CLI. Treat raw
> `kubectl`, `helm`, SSH, provider CLI/API, `docker exec`, and direct container
> access as platform bootstrap or documented break-glass only, and record any
> missing Enclii adapter gap.


<!-- MADFAM-AGENTS-CANONICAL v1 -->

This is the canonical instruction file for Claude, Codex, and any other LLM
agent working in this repository. `CLAUDE.md` is kept only as a compatibility
redirect and should not become the source of truth again.

## Required operating doctrine

- Read this file before making repo changes.
- Prefer existing repo conventions, scripts, and docs over introducing new
  patterns.
- Preserve user work and never revert unrelated changes.
- Treat production operations as Enclii-first: use Enclii web, API, or CLI for
  provisioning, deployment, observability, domains, secrets, provider
  operations, scaling, rollback, and remediation.
- Use direct `kubectl`, `helm`, SSH, provider CLIs/APIs, `docker exec`, or
  direct container access only for platform bootstrap or documented break-glass
  emergencies when Enclii is unavailable or lacks an implemented adapter.
- Record any missing Enclii adapter gap instead of normalizing raw production
  access in docs or runbooks.

## Repo entrypoints

- `README.md`
- `ECOSYSTEM.md`
- `docs/`
- `infra/`
- `.github/workflows/`

## LLM context files

- `llms.txt` is the compact context index.
- `llms-full.txt` is the durable full-context map and operating contract.
- `AGENTS.md` is canonical for agent instructions.
- `CLAUDE.md` redirects here for Claude compatibility.

## Maintenance

Regenerate or repair these files with
`internal-devops/scripts/sync-agent-docs.py` from the labspace ecosystem.

---

## Legacy CLAUDE.md guidance imported on 2026-05-13

<!-- BEGIN LEGACY_CLAUDE_IMPORT -->

# Bloom Scroll - CLAUDE.md

> **From Doom Scrolling to Bloom Scrolling**

## Overview

**Status**: 🟡 Experimental / Research Phase  
**Purpose**: Perspective-driven content aggregator optimizing for serendipity over engagement  
**License**: MPL 2.0  
**Philosophy**: The "Slow Web" - finite feeds, raw data, epistemic progress

Bloom Scroll counters infinite scrolling by providing **finite, intentional feeds** that leave users feeling informed and optimistic. Core principle: **"The End" is the product.**

---

## Quick Start

```bash
cd bloom-scroll

# Backend (FastAPI)
cd backend
python -m venv venv
source venv/bin/activate
poetry install
uvicorn app.main:app --reload --port 5200

# Frontend (Flutter - if available)
cd frontend
flutter pub get
flutter run -d chrome
```

---

## The "Slow Web" Philosophy

### 1. Finite Feeds (20-Item Daily Limit)
- Hard cap of **20 cards per day**
- Completion celebrated with "The Garden is Watered" message
- No "Load More" escape hatch
- Daily reset encourages routine

### 2. Upward Scrolling (Reverse Chronology)
- Users "plant" seeds at the bottom
- Scroll **up** to see ideas bloom
- Newest content appears at bottom (like chat)
- Natural stopping point at top

### 3. Raw Data Over Cooked Media
- Render charts from source CSV/JSON
- Interactive visualizations with fl_chart
- Preserve data provenance and context
- "Show your work" transparency

### 4. Serendipity Over Similarity
- Penalize echo chambers (cosine distance 0.3-0.8)
- Prioritize blindspot perspectives
- Mix aesthetics + data + science
- "Robin Hood" visual rhythm

---

## Project Structure

```
bloom-scroll/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI application
│   │   ├── models/           # Pydantic models
│   │   ├── services/
│   │   │   ├── aggregator.py # Content aggregation
│   │   │   ├── embeddings.py # Sentence-BERT embeddings
│   │   │   └── curation.py   # Serendipity algorithm
│   │   └── api/
│   │       └── routes.py     # API endpoints
│   ├── pyproject.toml        # Poetry deps (preferred)
│   └── tests/
├── frontend/                  # Flutter app (if present)
│   ├── lib/
│   │   ├── screens/
│   │   ├── widgets/
│   │   └── services/
│   └── pubspec.yaml
└── README.md
```

---

## Development Commands

### Backend (FastAPI)
```bash
cd backend

# Setup
python -m venv venv
source venv/bin/activate
poetry install

# Run
uvicorn app.main:app --reload --port 5200

# Tests
pytest
pytest --cov=app tests/
```

### Frontend (Flutter)
```bash
cd frontend

flutter pub get       # Install dependencies
flutter run -d chrome # Run in browser
flutter build web     # Production build
flutter test          # Run tests
```

---

## Tech Stack

### Backend
- **FastAPI** (Python 3.11+) - Async REST API
- **PostgreSQL 15+** with **pgvector** - Vector similarity search
- **Sentence-BERT** (all-MiniLM-L6-v2) - 384-dim embeddings
- **Redis** - Caching and rate limiting

### Frontend
- **Flutter 3.0+** - Cross-platform UI
- **fl_chart** - Interactive data visualization
- **Riverpod** - State management

---

## Port Allocation

| Service | Port | Description |
|---------|------|-------------|
| API (local) | 5200 | FastAPI backend |
| Web (local) | 5201 | Flutter web app |
| PostgreSQL | 5432 | Database |
| Redis | 6379 | Cache |

### Production (K8s)

| Service | Container Port | Runs As | Probe Path |
|---------|----------------|---------|------------|
| `bloom-scroll-api` | 8000 | uid 1001 | `/health` (unprefixed, PR #39) |
| `bloom-scroll-web` | 8080 | uid 1001, nginx non-root (PR #38) | `/` |

nginx needs a non-privileged port (<1024 is blocked for uid 1001) and rewrites its pid/cache/temp paths to `/tmp` so the non-root user can write — see `frontend/Dockerfile` for the full config. The API `/health` route is defined directly on the FastAPI app (not under `/api/v1/*`), so probes must target the unprefixed path.

---

## Content Sources

Bloom Scroll aggregates from diverse, high-signal sources:

### Statistical Truth
- Our World in Data
- FRED Economic Data
- UN Data
- World Bank Open Data

### Frontier Science
- arXiv (cs, physics, biology)
- PubMed
- bioRxiv/medRxiv

### Visual Culture
- Behance
- Dribbble
- Museums (Met, Rijks)

### Constructive News
- Positive News
- Solutions Journalism Network
- Good News Network

---

## Serendipity Algorithm

### Diversity Optimization
```python
# Penalize similarity, reward diversity
for candidate in candidates:
    distances = [cosine_distance(candidate, selected) for selected in feed]
    if min(distances) < 0.3:  # Too similar
        penalty += 0.5
    if 0.3 <= min(distances) <= 0.8:  # Sweet spot
        bonus += 0.3
```

### Content Type Rhythm
```python
# "Robin Hood" pattern - mix content types
rhythm = ["data", "science", "visual", "news", "data", ...]
for i, slot in enumerate(daily_slots):
    preferred_type = rhythm[i % len(rhythm)]
    candidates = filter_by_type(candidates, preferred_type)
```

### Blindspot Detection
```python
# Track user's perspective gaps
user_embedding_centroid = mean(user_interactions)
for candidate in candidates:
    if cosine_distance(candidate, user_embedding_centroid) > 0.7:
        # This is a blindspot - boost it
        candidate.score *= 1.5
```

---

## API Endpoints

```
# Feed
GET  /api/v1/feed              # Today's 20 items
GET  /api/v1/feed/archive      # Past feeds
POST /api/v1/feed/complete     # Mark feed complete

# Interactions
POST /api/v1/items/:id/view    # Track view
POST /api/v1/items/:id/save    # Save for later
POST /api/v1/items/:id/hide    # Hide from future

# User
GET  /api/v1/user/blindspots   # Perspective gaps
GET  /api/v1/user/stats        # Engagement stats
```

---

## Environment Variables

```bash
# Database
DATABASE_URL=postgresql://bloom:bloom@localhost:5432/bloom_scroll

# Redis
REDIS_URL=redis://localhost:6379

# Embeddings
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384

# Feed Configuration
DAILY_FEED_LIMIT=20
DIVERSITY_THRESHOLD=0.3
SERENDIPITY_FACTOR=0.5
```

---

## Design Principles

### UI/UX
- **Completion Widget**: Celebrate finishing ("The Garden is Watered")
- **Progress Indicator**: "12/20 seeds planted"
- **No Infinite Scroll**: Definitive end to each session
- **Upward Flow**: New content at bottom, completion at top

### Visual Aesthetic
- Nature-inspired color palette
- Calm, focused typography
- Generous whitespace
- Minimal chrome/distractions

### Data Visualization
- Interactive charts (not static images)
- Source attribution always visible
- Drill-down to raw data
- Mobile-friendly touch interactions

---

## Testing

```bash
# Backend
cd backend
pytest
pytest --cov=app --cov-report=html

# Frontend
cd frontend
flutter test
flutter test --coverage
```

---

## Related Projects

| Project | Relationship |
|---------|--------------|
| **Fortuna** | Problem intelligence (complementary signals) |
| **ForgeSight** | Data infrastructure patterns |
| **Dhanam** | ESG scoring methodology |

---

## Research Goals

- [ ] Measure impact on user wellbeing vs traditional feeds
- [ ] Optimize diversity without sacrificing relevance
- [ ] Test finite feed hypothesis at scale
- [ ] Develop "epistemic nutrition" metrics

---

*Bloom Scroll - The Slow Web | 20 Items. Then Stop.*

## Known Issues — Audits 2026-04-23 and 2026-05-28

See `/Users/aldoruizluna/labspace/claudedocs/ECOSYSTEM_AUDIT_2026-04-23.md` for the full ecosystem audit.
See `docs/CURRENT_STATE.md` for the 2026-05-28 repo/prod evidence snapshot.

- ~~**🟠 H5: Wildcard CORS**~~ — Fixed 2026-04-23: `backend/app/main.py` reads `CORS_ALLOWED_ORIGINS` env with `almanac.solar` fallback; explicit method + header lists.
- **🟠 H9: OpenAPI docs exposed in production** — Code gates docs on production env, but `https://api.almanac.solar/docs` and `/openapi.json` returned HTTP 200 on 2026-05-28. Manifest remediation stages `ENV=production`; verify after rollout.
- ~~**🟠 Local docs/test drift**~~ — Fixed in current working tree: backend health, feed, and poison-pill tests now target current modules/endpoints.
- **🟡 Root Compose** — Root `docker-compose.yml` is a compatibility stack; use `infrastructure/` Compose files for primary local development.

<!-- END LEGACY_CLAUDE_IMPORT -->
