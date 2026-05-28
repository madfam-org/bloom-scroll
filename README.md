# 🌱 Bloom Scroll

**From Doom Scrolling to Bloom Scrolling**

A perspective-driven content aggregator that counters infinite scrolling by optimizing for **serendipity**, **finite feeds**, and **raw data** instead of engagement and outrage.

---

## 🎯 Mission

Transform the endless scroll into a finite, intentional experience that leaves users feeling more informed and optimistic. Bloom Scroll synthesizes diverse content sources—from statistical truth to frontier science to visual culture—into a curated daily digest rooted in **epistemic progress** and **constructive perspective**.

**Core Principle**: "The End" is the product. Every feed has a definitive stopping point.

---

## 🌸 The "Slow Web" Philosophy

Bloom Scroll is built on four anti-doomscroll principles:

### 1. **Finite Feeds** (20-Item Daily Limit)
- Hard cap of **20 cards per day**
- Completion celebrated with "The Garden is Watered" message
- No "Load More" escape hatch
- Daily reset encourages routine

### 2. **Upward Scrolling** (Reverse Chronology)
- Users "plant" seeds at the bottom
- Scroll **up** to see ideas bloom
- Newest content appears at bottom (like chat)
- Natural stopping point at top (completion widget)

### 3. **Raw Data Over Cooked Media**
- Render charts from source CSV/JSON (not screenshots)
- Interactive visualizations with fl_chart
- Preserve data provenance and context
- "Show your work" transparency

### 4. **Serendipity Over Similarity**
- Penalize echo chambers (cosine distance 0.3-0.8)
- Prioritize blindspot perspectives
- Mix aesthetics + data + science
- "Robin Hood" visual rhythm

---

## 🛠️ Tech Stack

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688?style=flat&logo=fastapi&logoColor=white)
![Flutter](https://img.shields.io/badge/Flutter-3.0+-02569B?style=flat&logo=flutter&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791?style=flat&logo=postgresql&logoColor=white)
![pgvector](https://img.shields.io/badge/pgvector-0.5+-336791?style=flat&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-24.0+-2496ED?style=flat&logo=docker&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7.0+-DC382D?style=flat&logo=redis&logoColor=white)

### Backend
- **FastAPI** (Python 3.11+) - Async REST API
- **PostgreSQL** (15+) with **pgvector** - Vector similarity search
- **Sentence-BERT** (all-MiniLM-L6-v2) - 384-dim embeddings
- **Redis** - Caching and session management

### Frontend
- **Flutter/Dart** - Cross-platform web/mobile UI
- **Riverpod** - State management
- **fl_chart** - Interactive data visualization
- **Masonry Grid** - Staggered layout (Pinterest-style)

### Infrastructure
- **Docker Compose** - Local development
- **Alembic** - Database migrations
- **Kubernetes + ArgoCD** - Production deployment for `almanac.solar`

## ✅ Current State

**Last audited**: 2026-05-28. See [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md) for the evidence log from repository inspection and public production probes.

Key observed facts:
- Public web: `https://almanac.solar` returns HTTP 200.
- Public API health: `https://api.almanac.solar/health` returns healthy with database OK, 8 indexed embeddings, and 8 cards.
- The production Flutter bundle is baked to `https://api.almanac.solar/api/v1`.
- `/docs` and `/openapi.json` are hidden in production and covered by `scripts/prod-smoke.sh`.
- Backend installs are deterministic through `backend/poetry.lock`; production ML wheels are pinned separately in `backend/requirements-ml-linux-cpu.txt` so Linux images use CPU-only PyTorch.
- Enclii reports the `bloom-scroll-services` Argo app healthy/synced at `argocd-a84a3de`; API and web are both healthy at `2/2` replicas.
- Root `docker-compose.yml` is a lightweight compatibility stack on API port `5200`; `infrastructure/` remains the preferred local development path.

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- (Optional) Python 3.11+ for backend development
- (Optional) Flutter SDK 3.0+ for frontend development

### 1. Start local infrastructure 🌱
```bash
cd infrastructure
docker-compose -f docker-compose.dev.yml up -d
```

This starts:
- PostgreSQL with pgvector extension
- Redis cache

### 2. Run backend migrations 🗄️
```bash
cd ../backend
poetry install
poetry run alembic upgrade head
```

Creates the `bloom_cards` table with vector columns.

### 3. Start the API
```bash
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The local API runs at `http://localhost:8000`.

### 4. Seed content 🌾
```bash
curl -X POST "http://localhost:8000/api/v1/ingest/owid/all"
curl -X POST "http://localhost:8000/api/v1/ingest/aesthetics/all?limit_per_channel=2"
```

### 5. Run the Flutter app 📱
```bash
cd frontend
flutter pub get
flutter run -d chrome --dart-define=API_BASE_URL=http://localhost:8000
```

**API Endpoints**:
- iOS Simulator: `http://localhost:8000`
- Android Emulator: `http://10.0.2.2:8000`
- Physical Device: `http://<your-ip>:8000`

**View local API docs**: http://localhost:8000/docs

---

## 📁 Directory Structure

```
bloom-scroll/
├── 📖 docs/                          # Documentation & Architecture
│   ├── brief.md                      # Product concept
│   ├── prd.md                        # Product Requirements Document
│   ├── CURRENT_STATE.md              # Evidence-backed current implementation and prod state
│   ├── ARCHITECTURE.md               # Technical deep dive
│   ├── DESIGN_SYSTEM.md              # "Paper & Ink" design tokens
│   ├── ROADMAP.md                    # Story tracking (STORY-001 to STORY-007)
│   ├── design_tokens.md              # Raw design specifications
│   ├── STORY-004-IMPLEMENTATION.md   # Serendipity algorithm docs
│   ├── STORY-006-IMPLEMENTATION.md   # Perspective overlay docs
│   └── STORY-007-IMPLEMENTATION.md   # Finite feed docs
│
├── 🐍 backend/                       # Python FastAPI
│   ├── app/
│   │   ├── models/                   # SQLAlchemy models (BloomCard)
│   │   ├── ingestion/                # Implemented OWID + Are.na connectors
│   │   ├── curation/                 # Bloom algorithm (serendipity)
│   │   ├── analysis/                 # NLP models (SBERT, BiasBERT)
│   │   ├── api/                      # REST endpoints
│   │   └── core/                     # Database, config
│   ├── alembic/                      # Database migrations
│   ├── tests/                        # Pytest tests
│   ├── Dockerfile
│   ├── pyproject.toml                # Poetry dependencies
│   └── README.md
│
├── 🎨 frontend/                      # Flutter/Dart
│   ├── lib/
│   │   ├── models/                   # Dart data models (BloomCard, Feed)
│   │   ├── screens/                  # Feed screen, settings
│   │   ├── widgets/                  # Cards, perspective overlay, completion
│   │   ├── providers/                # Riverpod state management
│   │   ├── services/                 # API client, storage
│   │   └── theme/                    # Design tokens (colors, typography)
│   ├── assets/                       # Images, icons
│   ├── test/                         # Flutter tests
│   ├── pubspec.yaml                  # Dependencies
│   └── README.md
│
├── 🏗️ infrastructure/                # Local Docker Compose stacks
│   ├── docker-compose.dev.yml        # Postgres + Redis for host-run backend
│   └── docker-compose.yml            # Full local stack
│
├── docker-compose.yml                # Legacy root Compose file; see docs/CURRENT_STATE.md
└── README.md                         # This file
```

---

## 🎨 Design Philosophy

**"Paper & Ink"** - The UI feels like a printed Sunday newspaper, not a software application.

- **High Contrast**: Black ink (`#1A1A1A`) on warm paper (`#FDFCF8`)
- **No Shadows**: Use borders and whitespace for hierarchy
- **Data First**: Charts are the "hero" images, not decorations
- **Botanical Colors**: Growth green (`#2D6A4F`) for positive trends

See [DESIGN_SYSTEM.md](docs/DESIGN_SYSTEM.md) for complete specifications.

---

## 📊 Content Sources

Six content types blended into unified **BloomCard** format:

| Type | Source | Purpose |
|------|--------|---------|
| 📈 **Data** | Our World in Data | Statistical truth, macro trends |
| 🔬 **Science** | OpenAlex | Frontier research, academic papers |
| 🎨 **Aesthetic** | Are.na / CARI | Visual culture, design inspiration |
| 🌐 **Indie Web** | Neocities | Human-made web, small internet |
| 📖 **Narrative** | TVTropes | Story patterns, cultural analysis |
| 🎓 **Education** | My-MOOC | Free courses, skill building |

---

## 🧪 Development

### Backend Development
```bash
cd backend

# Install dependencies (Poetry)
poetry install

# Run tests
poetry run pytest

# Code quality
poetry run black .
poetry run ruff check .
poetry run mypy . --ignore-missing-imports

# Database migrations
poetry run alembic revision --autogenerate -m "Description"
poetry run alembic upgrade head

# Start dev server
poetry run uvicorn app.main:app --reload
```

### Frontend Development
```bash
cd frontend

# Install dependencies
flutter pub get

# Generate code (Riverpod, JSON serialization)
flutter pub run build_runner build --delete-conflicting-outputs

# Run tests
flutter test

# Static analysis
flutter analyze --no-fatal-infos

# Build for release
flutter build web --release --dart-define=API_BASE_URL=http://localhost:8000
```

---

## 📚 Documentation

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Technical deep dive (Root System, Perspective Engine, Bloom Logic)
- **[DESIGN_SYSTEM.md](docs/DESIGN_SYSTEM.md)** - "Paper & Ink" design tokens and guidelines
- **[ROADMAP.md](docs/ROADMAP.md)** - Story tracking (STORY-001 to STORY-007)
- **[CURRENT_STATE.md](docs/CURRENT_STATE.md)** - Evidence-backed implementation and production state
- **[STABILITY_SESSION_2026-05-28.md](docs/STABILITY_SESSION_2026-05-28.md)** - 2026-05-28 stabilization session wrap-up
- **[Product Brief](docs/brief.md)** - Core concept and differentiators
- **[PRD](docs/prd.md)** - Detailed product requirements

### Implementation Docs
- **[STORY-004](docs/STORY-004-IMPLEMENTATION.md)** - Serendipity algorithm & vector search
- **[STORY-006](docs/STORY-006-IMPLEMENTATION.md)** - Perspective overlay & 3D flip animation
- **[STORY-007](docs/STORY-007-IMPLEMENTATION.md)** - Finite feed & completion widget

---

## 🗺️ Current Status

**Version**: 0.1.0
**Phase**: Production alpha / stabilization
**Last Updated**: 2026-05-28

### Completed Stories ✅
- ✅ **STORY-001**: Infrastructure & OWID Ingestion
- ✅ **STORY-002**: Flutter Scaffold & Charting
- ✅ **STORY-003**: Aesthetics & Masonry Grid
- ✅ **STORY-004**: Vector Serendipity & Bias Engine
- ✅ **STORY-006**: Perspective Overlay & Flip Animation
- ✅ **STORY-007**: Finite Feed & Completion Widget

### Needs Verification / Hardening 🚧
- ✅ **STORY-005 backend repair**: Poison pill and feed tests now target current modules/endpoints.
- ✅ **Production docs exposure**: `/docs` and `/openapi.json` are hidden on `api.almanac.solar` by the production environment gate and covered by `scripts/prod-smoke.sh`.
- ✅ **Auth hardening**: Janua RS256/JWKS verification is implemented with issuer and optional audience checks.
- ✅ **OpenAlex ingestion**: Science cards now have a repo-owned connector and API endpoints.
- ✅ **Control-plane observability release**: Enclii CLI `v1.0.0-alpha.1` reports runtime health correctly from the distributed GitHub release artifact.
- ✅ **Backend dependency determinism**: `backend/poetry.lock` is committed, CPU-only ML wheels are pinned separately for Docker, and lockfile guard tests prevent CUDA drift.
- 🔜 **Next stability priority**: frontend E2E/stress coverage, production observability, and load/soak testing.

See [ROADMAP.md](docs/ROADMAP.md) for detailed tracking.

---

## 🌱 Core Principles

1. **Finite Feeds**: Respect user time with definitive endpoints
2. **Serendipity**: High-value outliers over echo chambers
3. **Transparency**: Show data provenance and bias scores
4. **Privacy**: No tracking sold to third parties

---

## 📄 License

Proprietary - Bloom Scroll Team

---

**Built with intention. Consumed with mindfulness.** 🌸
