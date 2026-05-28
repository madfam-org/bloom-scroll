# 🏗️ Bloom Scroll: Technical Architecture

**The Map** - A comprehensive guide to the technical flow and implementation

**Last audited**: 2026-05-28. See [CURRENT_STATE.md](CURRENT_STATE.md) for evidence from repository inspection and `almanac.solar` production probes.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Flutter Web/Mobile Client                  │
│     (Masonry Grid, Flip Animation, Completion Widget)       │
└─────────────────┬────────────────────────────────────────────┘
                  │ REST API (JSON)
┌─────────────────▼────────────────────────────────────────────┐
│                    FastAPI Backend                            │
│  ┌──────────────┬──────────────┬──────────────┬──────────┐  │
│  │  Ingestion   │   Analysis   │  Curation    │   API    │  │
│  │ (OWID,Are.na)│  (SBERT,NLP) │ (Bloom Algo) │ Routes   │  │
│  └──────────────┴──────────────┴──────────────┴──────────┘  │
└─────────────────┬────────────────────────────────────────────┘
                  │
    ┌─────────────┼─────────────┬─────────────────┐
    │             │             │                 │
┌───▼────┐  ┌────▼─────┐  ┌────▼────┐      ┌────▼─────┐
│PostGres│  │ pgvector │  │  Redis  │      │ External │
│   DB   │  │(Embeddings)│ │ (Cache) │      │   APIs   │
└────────┘  └──────────┘  └─────────┘      └──────────┘
```

---

## 🌱 The Root System (Ingestion)

**Purpose**: Fetch and normalize content from diverse sources into a unified `BloomCard` format.

### Polymorphic Data Model

All content types share a common schema but use `data_payload` (JSONB) for source-specific data:

```python
class BloomCard:
    id: UUID
    source_type: str  # "OWID", "OPENALEX", "CARI", "NEOCITIES", etc.
    title: str
    summary: Optional[str]  # LLM-generated for aesthetics/science
    original_url: str
    data_payload: Dict  # Polymorphic: chart_config | image_url | abstract

    # Perspective metadata
    bias_score: Optional[float]  # -1.0 (left) to +1.0 (right)
    constructiveness_score: Optional[float]  # 0.0 to 100.0
    blindspot_tags: Optional[List[str]]

    # Bloom logic
    embedding: Optional[Vector[384]]  # Sentence-BERT
    created_at: datetime
```

### Content Types

#### 📊 Charts (OWID)
**Source**: Our World in Data CSV/JSON APIs
**Payload**:
```json
{
  "chart_type": "line",
  "years": [2000, 2001, 2002, ...],
  "values": [10.2, 10.5, 10.8, ...],
  "unit": "%",
  "indicator": "Life Expectancy",
  "entity": "World"
}
```

**Ingestion**:
- Direct CSV parsing (no scraping)
- Fetch last 20 years of data
- Store as JSON in `data_payload`
- Generate embedding from title + indicator

#### 🎨 Aesthetics (Are.na)
**Source**: Are.na API (channel blocks)
**Payload**:
```json
{
  "image_url": "https://...",
  "aspect_ratio": 0.75,
  "dominant_color": "#8C7A6B",
  "vibe_tags": ["brutalist", "y2k"],
  "arena_block_id": 12345
}
```

**Ingestion**:
- Query Are.na public channels
- Pre-calculate aspect ratio (prevent layout shifts)
- Dominant color extraction helper exists, but ingestion currently stores `#808080`
- Cache images via CDN

#### 🔬 Science (OpenAlex)
**Source**: OpenAlex API (academic papers)
**Payload**:
```json
{
  "abstract": "This paper examines...",
  "authors": ["Smith, J.", "Doe, A."],
  "pdf_url": "https://...",
  "cited_by_count": 42,
  "concepts": ["climate", "modeling"]
}
```

`backend/app/ingestion/openalex.py` fetches OpenAlex works, reconstructs
`abstract_inverted_index`, preserves authors/source/OpenAlex IDs/PDF URLs, and
exposes ingestion through `/api/v1/ingest/openalex`.

### Data Flow

```
External Source
    ↓
Spider/Client (ingestion/)
    ↓
Validator (Pydantic schemas)
    ↓
Embedder (Sentence-BERT)
    ↓
BloomCard.to_dict()
    ↓
PostgreSQL (bloom_cards table)
```

---

## 🧠 The Perspective Engine (Analysis)

**Purpose**: Score content quality, detect bias, and cluster perspectives.

### Components

#### 1. Sentence-BERT Embeddings
**Model**: `all-MiniLM-L6-v2` (384 dimensions)
**Purpose**: Semantic similarity for serendipity scoring

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')
text = f"{card.title} {card.summary or ''}"
embedding = model.encode(text, convert_to_numpy=True)
# → [0.123, -0.456, 0.789, ...] (384 dims)
```

**Storage**: pgvector column on `bloom_cards.embedding`. The current feed algorithm loads recent candidates and filters distance in Python; future optimization can push distance filtering deeper into pgvector queries.

```sql
CREATE EXTENSION IF NOT EXISTS vector;
ALTER TABLE bloom_cards ADD COLUMN embedding vector(384);
CREATE INDEX ON bloom_cards USING ivfflat (embedding vector_cosine_ops);
```

#### 2. Bias Classification (Future - PoliticalBiasBERT)
**Model**: `bucketresearch/politicalBiasBERT`
**Output**: Bias score from -1.0 (left) to +1.0 (right)

**Current Implementation**: `NLPProcessor.detect_bias()` is a placeholder returning `None`
**Future**: Real-time inference for news/opinion content

#### 3. Constructiveness Scoring
**Scale**: 0.0 to 100.0
- **< 50**: High noise (emotional language, partisan framing)
- **50-80**: Mixed signal (factual + opinion)
- **> 80**: High signal (well-sourced, balanced)

**Current**: API output falls back to `50.0` when `constructiveness_score` is null
**Future**: Fine-tuned transformer on constructive vs. inflammatory content

#### 4. Blindspot Detection
**Method**: User consumption clustering (target design)
**Tags**: `["conservative-blindspot", "global-south-blindspot", ...]`

**Target algorithm**:
1. Build user's consumption vector (average of read card embeddings)
2. Cluster all content using HDBSCAN
3. Identify underrepresented clusters
4. Tag content from those clusters as "blindspot breakers"

---

## 🎲 The Bloom Logic (Serendipity)

**Purpose**: Generate feeds that balance relevance and novelty.

### Core Algorithm: Cosine Distance Thresholding

```python
class BloomAlgorithm:
    def __init__(self, min_distance=0.3, max_distance=0.8):
        self.min_distance = min_distance  # Avoid echo chamber
        self.max_distance = max_distance  # Avoid irrelevance

    async def generate_feed(self, session, user_context_ids=None, limit=20):
        if not user_context_ids:
            return await self._get_recent_cards(session, limit)

        context_vector = await self._calculate_user_context(session, user_context_ids)
        candidates = await self._query_serendipity_zone(session, context_vector, limit)
        return candidates
```

Current implementation note: `_query_serendipity_zone()` fetches recent embedded cards, computes cosine distance in Python, sorts by proximity to the zone midpoint, and returns up to `limit`. It does not currently enforce source balancing.

### The "Serendipity Zone"

```
         Echo Chamber      Serendipity Zone      Irrelevant
         ▼                 ▼                     ▼
    |─────────────|─────────────────────|─────────────|
    0.0          0.3                   0.8           1.0
                  ▲                     ▲
                  min_distance          max_distance
```

- **< 0.3**: Too similar (boring, filter bubble)
- **0.3 - 0.8**: Sweet spot (related but novel)
- **> 0.8**: Too different (confusing, irrelevant)

### Reason Tag Generation

```python
def calculate_reason_tag(self, card, context_vector):
    distance = cosine_distance(card.embedding, context_vector)

    if card.blindspot_tags:
        return "BLINDSPOT_BREAKER"  # 🌱
    elif distance > 0.6:
        return "EXPLORE"  # 🗺️
    elif distance > 0.4:
        return "PERSPECTIVE_SHIFT"  # 🔄
    elif distance < 0.4:
        return "DEEP_DIVE"  # ⚓
    else:
        return "SERENDIPITY"  # ✨
```

### Source Balancing ("Robin Hood Layout")

Source balancing is a product goal and UI rhythm principle. It is not currently implemented as a backend `_balance_sources()` method.

```python
# Target future shape:
# interleave OWID, AESTHETIC, OPENALEX, and future source types
# after serendipity/quality filtering.
```

---

## ⏱️ The Finite State (Daily Limits)

**Purpose**: Enforce **20-card daily limit** to prevent infinite scrolling.

### Backend Pagination

```python
DAILY_LIMIT = 20

@router.get("/feed")
async def get_feed(
    page: int = 1,
    read_count: int = 0,  # Cards already read today
    limit: int = 10,
    user_context: Optional[List[str]] = None,
):
    # Calculate remaining cards
    remaining = DAILY_LIMIT - read_count

    if remaining <= 0:
        # Return completion object
        return {
            "cards": [],
            "completion": {
                "type": "COMPLETION",
                "message": "The Garden is Watered.",
                "subtitle": "You've reached today's limit..."
            }
        }

    # Clamp limit to remaining
    effective_limit = min(limit, remaining)

    # Generate feed
    cards = bloom.generate_feed(user_context, effective_limit)

    # Check if this is the last page
    new_total = read_count + len(cards)
    has_next = new_total < DAILY_LIMIT

    return {
        "cards": cards,
        "pagination": {
            "page": page,
            "has_next_page": has_next,
            "total_read_today": new_total,
            "daily_limit": DAILY_LIMIT
        },
        "completion": None if has_next else {...}
    }
```

### Frontend State Management (Riverpod)

```dart
class FeedController extends StateNotifier<FeedState> {
  final ApiService _api;
  final StorageService _storage;

  Future<void> loadFeed() async {
    // Get current read count from local storage
    final readCount = await _storage.getReadCount();

    // Fetch from API with current state
    final response = await _api.getFeed(
      page: state.currentPage,
      readCount: readCount,
      limit: 10,
    );

    // Update state
    state = FeedState(
      cards: [...state.cards, ...response.cards],
      pagination: response.pagination,
      completion: response.completion,
    );
  }

  Future<void> markCardAsRead(String cardId) async {
    await _storage.markCardAsRead(cardId);
    // Update local read count
    await _storage.incrementReadCount();
  }
}
```

### Daily Reset (Local Storage)

```dart
class StorageService {
  Future<void> _checkAndResetDaily() async {
    final lastResetDate = prefs.getString('last_reset_date');
    final today = DateTime.now().toIso8601String().split('T')[0];

    if (lastResetDate != today) {
      // New day! Reset counters
      await prefs.setInt('read_count', 0);
      await prefs.setStringList('read_card_ids', []);
      await prefs.setString('last_reset_date', today);
    }
  }
}
```

---

## 🎨 Frontend Architecture

### Widget Hierarchy

```
FeedScreen (StatefulWidget)
├── ScrollController (pagination trigger)
├── AppBar
│   └── Progress Indicator (10/20)
├── LinearProgressIndicator (visual progress bar)
└── CustomScrollView (reverse: true)
    ├── CompletionWidget (if complete)
    ├── SliverMasonryGrid
    │   ├── OwidCard (wrapped in FlippableCard)
    │   │   ├── fl_chart LineChart
    │   │   └── PerspectiveOverlay (on flip)
    │   └── AestheticCard (wrapped in FlippableCard)
    │       ├── CachedNetworkImage
    │       └── PerspectiveOverlay (on flip)
    └── Loading Indicator (if loading more)
```

### State Management (Riverpod)

```
Providers:
- apiServiceProvider: ApiService singleton
- storageServiceProvider: StorageService singleton
- feedControllerProvider: StateNotifier<FeedState>

State Flow:
User scrolls → _onScroll() → Check threshold → loadNextPage()
  → FeedController.loadNextPage()
  → ApiService.getFeed()
  → Update FeedState
  → UI rebuilds
```

### Key Widgets

#### FlippableCard
- 3D Y-axis rotation using Matrix4
- 300ms animation duration
- Info icon (ⓘ) triggers flip
- Front: Original card content
- Back: PerspectiveOverlay

#### PerspectiveOverlay
- BiasCompass: Political spectrum visualization
- ConstructivenessRing: Radial gauge (CustomPainter)
- SerendipityTag: "Why this card?" reason display

#### CompletionWidget
- Animated flower icon (scale + rotate)
- "The Garden is Watered" message
- Stats display (20/20)
- Encourages return tomorrow

---

## 📊 Data Models

### BloomCard (Backend - SQLAlchemy)

```python
class BloomCard(Base):
    __tablename__ = "bloom_cards"

    id = Column(UUID, primary_key=True)
    source_type = Column(String(50))  # OWID, AESTHETIC, OPENALEX, etc.
    title = Column(Text)
    summary = Column(Text, nullable=True)
    original_url = Column(Text)
    data_payload = Column(JSONB)  # Polymorphic content

    # Perspective metadata
    bias_score = Column(Float, nullable=True)
    constructiveness_score = Column(Float, nullable=True)
    blindspot_tags = Column(ARRAY(Text), nullable=True)

    # Bloom logic
    embedding = Column(Vector(384), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### BloomCard (Frontend - Dart)

```dart
class BloomCard {
  final String id;
  final String sourceType;
  final String title;
  final String? summary;
  final String originalUrl;
  final Map<String, dynamic> dataPayload;
  final PerspectiveMeta? meta;
  final DateTime createdAt;

  // Helper properties
  bool get isOwid => sourceType == 'OWID';
  bool get isAesthetic => sourceType == 'AESTHETIC';
  OwidChartData? get owidData;
  AestheticData? get aestheticData;
}
```

---

## 🔐 Security & Privacy

### Data Handling
- **No user tracking sold to third parties** is a product principle.
- Frontend read count and read card IDs are stored locally with `shared_preferences`.
- Server-side interaction tracking exists at `/api/v1/interactions/*`, but user data export/delete APIs are not implemented in this repo.
- Janua auth verifies production RS256 tokens through JWKS, issuer, and optional audience checks. HS algorithms are retained only as an explicit local development fallback.

### Rate Limiting
- Application-level API rate limiting is not implemented.
- OWID and Are.na connectors should be treated respectfully; explicit throttling is still future work.

---

## 🚀 Deployment

### Development (Docker Compose)
```bash
cd infrastructure
docker-compose -f docker-compose.dev.yml up -d

cd ../backend
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Services:
- PostgreSQL 15 with pgvector
- Redis 7 (cache)
- FastAPI backend (port 8000)

The root `docker-compose.yml` is a compatibility stack on host API port `5200`; prefer `infrastructure/` Compose files for documented development.

### Production (Kubernetes)
- Public web: `https://almanac.solar`
- Public API: `https://api.almanac.solar`
- API deployment: `bloom-scroll-api`, 2 replicas, container port `8000`, probes on `/health`
- Web deployment: `bloom-scroll-web`, 2 replicas, container port `8080`, probes on `/`
- Services expose ClusterIP port `80` targeting API `8000` and web `8080`
- Kustomize pins image digests in `infra/k8s/production/kustomization.yaml`

Observed production gaps on 2026-05-28:
- Enclii CLI observation requires explicit project context, for example `ENCLII_PROJECT=bloom-scroll enclii ps --env production`.
- The Enclii CLI `ps` health-parity fix is implemented upstream in `madfam-org/enclii@03e2847`, verified from source at `madfam-org/enclii@f919192`, and still needs normal CLI release propagation.
- Poetry lockfile adoption remains deferred because PyTorch CPU-wheel source handling needs to stay platform-safe for Linux images and macOS local development.

---

## 📈 Performance Considerations

### Backend Optimizations
- **pgvector indexing**: HNSW index migration exists for vector similarity
- **JSONB indexing**: GIN indexes on frequently queried payload fields
- **Redis caching**: configured, but hot-feed caching is not implemented
- **Async I/O**: FastAPI + asyncio for concurrent requests

### Frontend Optimizations
- **Masonry lazy loading**: Only render visible cards
- **Image caching**: cached_network_image with LRU cache
- **Skeleton screens**: shimmer placeholders during load
- **Append-only pagination**: No full list rebuild

---

## 🧪 Testing Strategy

### Backend
- **Unit/API tests**: pytest files exist under `backend/tests`
- **Backend test signal**: `poetry run pytest` passes health, feed, and poison-pill tests
- **Load tests**: not present in the repo

### Frontend
- **Tests**: no committed `frontend/test/` directory as of the audit
- **Planned**: widget tests, integration tests, golden tests, and Flutter DevTools performance profiling

---

**Version**: 2.1
**Last Updated**: 2026-05-28
**Maintainer**: Engineering Team
