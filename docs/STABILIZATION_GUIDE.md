# 🛡️ Bloom Scroll: Stabilization Guide

**Expert recommendations for production-ready stability**

**Last audited**: 2026-05-28. See [CURRENT_STATE.md](CURRENT_STATE.md) for current repo/prod evidence.

Current stabilization reality:
- Production is live at `almanac.solar` and `api.almanac.solar`.
- API health is green, but `/docs` and `/openapi.json` are public in production until the staged `ENV=production` deployment rolls out.
- Error handlers and Flutter `ErrorBoundary` are wired.
- Poison-pill tests were repaired to current module names and pass locally.
- Root `docker-compose.yml` is a compatibility stack; use `infrastructure/` Compose files for primary local development.

---

## Overview

This guide provides a comprehensive strategy to stabilize Bloom Scroll for production deployment. It covers backend resilience, frontend error handling, performance optimization, and monitoring.

---

## 1. Backend Stabilization

### 1.1 Error Handling ✅ IMPLEMENTED

**Global Error Handlers** (`backend/app/core/error_handlers.py`):
- Database connection failures → 503 Service Unavailable
- Validation errors → 422 Unprocessable Entity
- Unexpected exceptions → 500 Internal Server Error
- Logging to stderr (captured by Docker)

**Integration**:
```python
# backend/app/main.py
from app.core.error_handlers import register_error_handlers

app = FastAPI()
register_error_handlers(app)
```

### 1.2 Validation & Sanitization

**Input Validation**:
```python
# Use Pydantic models for all endpoints
from pydantic import BaseModel, validator, Field

class FeedRequest(BaseModel):
    page: int = Field(ge=1, le=100, default=1)
    limit: int = Field(ge=1, le=20, default=10)
    read_count: int = Field(ge=0, le=1000, default=0)

    @validator('user_context')
    def validate_uuids(cls, v):
        if v:
            for id_str in v:
                try:
                    UUID(id_str)
                except ValueError:
                    raise ValueError(f"Invalid UUID: {id_str}")
        return v
```

**Data Sanitization**:
```python
# backend/app/ingestion/owid.py
def parse_csv(self, csv_path: Path) -> List[BloomCard]:
    cards = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                # Validate required fields
                if not row.get('Year') or not row.get('Value'):
                    logger.warning(f"Skipping invalid row: {row}")
                    continue

                # Sanitize numeric values
                value = float(row['Value'])
                if not (-1e308 < value < 1e308):  # Valid float range
                    logger.warning(f"Skipping extreme value: {value}")
                    continue

                cards.append(self._create_card(row))
            except (ValueError, TypeError) as e:
                logger.warning(f"Skipping malformed row: {e}")
                continue

    return cards
```

### 1.3 Database Resilience

**Connection Pooling**:
```python
# backend/app/core/database.py
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,          # Max connections
    max_overflow=10,       # Additional connections if pool full
    pool_pre_ping=True,    # Test connection before use
    pool_recycle=3600,     # Recycle connections every hour
)
```

**Retry Logic**:
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def get_feed_with_retry(db: AsyncSession, **kwargs):
    return await bloom.generate_feed(db, **kwargs)
```

**Graceful Degradation**:
```python
# If embeddings fail, return recent cards
try:
    cards = await bloom.generate_feed(session, user_context_ids, limit)
except Exception as e:
    logger.error(f"Serendipity algorithm failed: {e}")
    # Fallback: Return most recent cards
    cards = await session.execute(
        select(BloomCard)
        .order_by(BloomCard.created_at.desc())
        .limit(limit)
    )
    cards = cards.scalars().all()
```

### 1.4 Rate Limiting

**Implement rate limiting for API endpoints**:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.get("/feed")
@limiter.limit("60/minute")  # 60 requests per minute
async def get_feed(...):
    ...
```

### 1.5 Poison Pill Tests ✅ REPAIRED

**Run gauntlet tests**:
```bash
cd backend
poetry run pytest tests/test_ingestion_gauntlet.py -v
```

Tests cover:
- Malformed CSV data
- Invalid image URLs
- Null/missing metadata
- Extreme numeric values
- Empty text embeddings
- Very long text (>512 tokens)
- Invalid API parameters

Audit note 2026-05-28: `backend/tests/test_ingestion_gauntlet.py` now targets `app.ingestion.owid`, `app.ingestion.aesthetics`, and `app.analysis.processor`.

---

## 2. Frontend Stabilization

### 2.1 Error Boundaries ✅ IMPLEMENTED

**Wrap critical widgets**:
```dart
// frontend/lib/main.dart
class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return ProviderScope(
      child: ErrorBoundary(
        child: MaterialApp(
          home: FeedScreen(),
        ),
      ),
    );
  }
}
```

**Per-widget error handling**:
```dart
// Wrap individual cards
ErrorBoundary(
  errorBuilder: (details) => _buildCardErrorFallback(),
  child: OwidCard(card: card),
)
```

### 2.2 Network Error Handling

**Retry with exponential backoff**:
```dart
// frontend/lib/services/api_service.dart
import 'package:dio/dio.dart';

class RetryInterceptor extends Interceptor {
  @override
  void onError(DioException err, ErrorInterceptorHandler handler) async {
    if (err.type == DioExceptionType.connectionTimeout ||
        err.type == DioExceptionType.receiveTimeout) {

      // Retry up to 3 times
      if (err.requestOptions.extra['retryCount'] < 3) {
        final retryCount = err.requestOptions.extra['retryCount'] + 1;
        err.requestOptions.extra['retryCount'] = retryCount;

        // Exponential backoff: 1s, 2s, 4s
        await Future.delayed(Duration(seconds: 1 << (retryCount - 1)));

        try {
          final response = await dio.fetch(err.requestOptions);
          return handler.resolve(response);
        } catch (e) {
          return handler.next(err);
        }
      }
    }

    handler.next(err);
  }
}

// Add to Dio instance
_dio.interceptors.add(RetryInterceptor());
```

**Offline mode detection**:
```dart
import 'package:connectivity_plus/connectivity_plus.dart';

class NetworkService {
  final Connectivity _connectivity = Connectivity();

  Stream<bool> get isOnline => _connectivity.onConnectivityChanged.map(
    (result) => result != ConnectivityResult.none,
  );

  Future<bool> checkConnection() async {
    final result = await _connectivity.checkConnectivity();
    return result != ConnectivityResult.none;
  }
}
```

### 2.3 Null Safety & Validation

**Ensure all models handle null gracefully**:
```dart
// frontend/lib/models/bloom_card.dart
factory BloomCard.fromJson(Map<String, dynamic> json) {
  try {
    return BloomCard(
      id: json['id'] as String? ?? '',
      sourceType: json['source_type'] as String? ?? 'UNKNOWN',
      title: json['title'] as String? ?? 'Untitled',
      summary: json['summary'] as String?,
      originalUrl: json['original_url'] as String? ?? '',
      dataPayload: json['data_payload'] as Map<String, dynamic>? ?? {},
      meta: json['meta'] != null
          ? PerspectiveMeta.fromJson(json['meta'])
          : null,
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'])
          : DateTime.now(),
    );
  } catch (e) {
    debugPrint('Error parsing BloomCard: $e');
    // Return a valid "error card" instead of throwing
    return BloomCard.errorCard(e.toString());
  }
}

static BloomCard errorCard(String error) {
  return BloomCard(
    id: 'error',
    sourceType: 'ERROR',
    title: 'Failed to load card',
    originalUrl: '',
    dataPayload: {'error': error},
    createdAt: DateTime.now(),
  );
}
```

### 2.4 Memory Management

**Dispose resources properly**:
```dart
// Ensure all controllers are disposed
@override
void dispose() {
  _scrollController.dispose();
  _animationController.dispose();
  super.dispose();
}
```

**Limit cached images**:
```dart
// frontend/lib/widgets/aesthetic_card.dart
CachedNetworkImage(
  imageUrl: imageUrl,
  memCacheWidth: 800,  // Limit memory usage
  maxHeightDiskCache: 1200,  // Limit disk cache
  errorWidget: (context, url, error) => _buildImageErrorWidget(),
)
```

---

## 3. Performance Optimization

### 3.1 Backend Performance

**Database Indexing**:
```sql
-- Ensure proper indexes exist
CREATE INDEX idx_bloom_cards_created_at ON bloom_cards(created_at DESC);
CREATE INDEX idx_bloom_cards_source_type ON bloom_cards(source_type);

-- Vector search index (pgvector)
CREATE INDEX idx_bloom_cards_embedding ON bloom_cards
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Analyze tables for query optimization
ANALYZE bloom_cards;
```

**Query Optimization**:
```python
# Use .options() for eager loading
cards = await session.execute(
    select(BloomCard)
    .options(selectinload(BloomCard.interactions))  # Prevent N+1 queries
    .limit(limit)
)
```

**Caching** (Redis):
```python
from redis import asyncio as aioredis
import json

async def get_feed_cached(cache_key: str, limit: int):
    redis = await aioredis.from_url("redis://localhost")

    # Try cache first
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    # Generate fresh feed
    feed = await bloom.generate_feed(limit=limit)

    # Cache for 5 minutes
    await redis.setex(
        cache_key,
        300,
        json.dumps([card.to_dict() for card in feed])
    )

    return feed
```

### 3.2 Frontend Performance

**Lazy loading in masonry grid**:
```dart
// Already implemented with flutter_staggered_grid_view
// Ensure viewport configuration
SliverMasonryGrid.count(
  crossAxisCount: 2,
  // Only build visible items + small buffer
  childCount: feedState.cards.length,
)
```

**Image optimization**:
```dart
CachedNetworkImage(
  imageUrl: imageUrl,
  progressIndicatorBuilder: (context, url, progress) =>
      Shimmer.fromColors(
        baseColor: BloomColors.skeletonBg,
        highlightColor: BloomColors.surfaceBg,
        child: Container(color: BloomColors.skeletonBg),
      ),
  fadeInDuration: const Duration(milliseconds: 200),
  memCacheWidth: 800,  // Resize for device
)
```

**Animation performance**:
```dart
// Use RepaintBoundary for expensive widgets
RepaintBoundary(
  child: FlippableCard(card: card),
)

// Limit animation complexity
AnimationController(
  duration: const Duration(milliseconds: 300),  // Fast!
  vsync: this,
)
```

---

## 4. Monitoring & Observability

### 4.1 Logging

**Structured logging (backend)**:
```python
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
        }
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        return json.dumps(log_data)

# Configure in main.py
logging.basicConfig(
    level=logging.INFO,
    handlers=[logging.StreamHandler()],
    format='%(message)s'
)
logging.getLogger().handlers[0].setFormatter(JSONFormatter())
```

**Frontend logging**:
```dart
import 'package:logger/logger.dart';

final logger = Logger(
  printer: PrettyPrinter(
    methodCount: 2,
    errorMethodCount: 8,
    lineLength: 120,
    colors: true,
    printEmojis: true,
  ),
);

// Use throughout app
logger.i('Feed loaded: ${feedState.cards.length} cards');
logger.e('API error', error: e, stackTrace: stackTrace);
```

### 4.2 Health Checks

**Backend health endpoint**:
```python
@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Comprehensive health check."""
    health = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }

    # Database check
    try:
        await db.execute(text("SELECT 1"))
        health["checks"]["database"] = "ok"
    except Exception as e:
        health["checks"]["database"] = f"error: {str(e)}"
        health["status"] = "unhealthy"

    # Redis check
    try:
        redis = await aioredis.from_url("redis://localhost")
        await redis.ping()
        health["checks"]["redis"] = "ok"
    except Exception as e:
        health["checks"]["redis"] = f"error: {str(e)}"
        health["status"] = "degraded"

    # Vector search check
    try:
        result = await db.execute(
            text("SELECT COUNT(*) FROM bloom_cards WHERE embedding IS NOT NULL")
        )
        count = result.scalar()
        health["checks"]["embeddings"] = f"ok ({count} vectors)"
    except Exception as e:
        health["checks"]["embeddings"] = f"error: {str(e)}"

    status_code = 200 if health["status"] == "healthy" else 503
    return JSONResponse(content=health, status_code=status_code)
```

### 4.3 Metrics (Future - Prometheus)

```python
from prometheus_client import Counter, Histogram, generate_latest

# Define metrics
feed_requests = Counter('feed_requests_total', 'Total feed requests')
feed_latency = Histogram('feed_latency_seconds', 'Feed generation latency')

@app.get("/feed")
@feed_latency.time()
async def get_feed(...):
    feed_requests.inc()
    # ... existing code

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

---

## 5. Testing Strategy

### 5.1 Unit Tests

**Backend**:
```bash
cd backend
poetry run pytest tests/ --cov=app --cov-report=html
```

**Frontend**:
```bash
cd frontend
flutter test --coverage
```

### 5.2 Integration Tests

**API tests**:
```python
# backend/tests/test_api_integration.py
@pytest.mark.asyncio
async def test_feed_end_to_end(client, db):
    """Test complete feed flow."""
    # 1. Ingest test data
    response = await client.post("/ingest/owid", params={"dataset_key": "co2_emissions"})
    assert response.status_code == 200

    # 2. Generate feed
    response = await client.get("/feed", params={"limit": 10})
    assert response.status_code == 200
    data = response.json()
    assert len(data["cards"]) == 10

    # 3. Check pagination
    response = await client.get("/feed", params={"page": 2, "limit": 10})
    assert response.status_code == 200
```

**Flutter integration tests**:
```dart
// frontend/integration_test/feed_flow_test.dart
testWidgets('Complete feed flow', (WidgetTester tester) async {
  await tester.pumpWidget(MyApp());

  // Wait for feed to load
  await tester.pumpAndSettle();

  // Verify cards displayed
  expect(find.byType(OwidCard), findsWidgets);
  expect(find.byType(AestheticCard), findsWidgets);

  // Test scroll pagination
  await tester.drag(find.byType(CustomScrollView), Offset(0, -500));
  await tester.pumpAndSettle();

  // Verify more cards loaded
  // ...
});
```

### 5.3 Load Testing

**Locust for API stress testing**:
```python
# backend/tests/load_test.py
from locust import HttpUser, task, between

class BloomScrollUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def get_feed(self):
        self.client.get("/feed?limit=20")

    @task(3)  # 3x more frequent
    def get_feed_with_context(self):
        self.client.get("/feed?limit=10&user_context=uuid1,uuid2")

# Run: locust -f backend/tests/load_test.py --host=http://localhost:8000
```

---

## 6. Deployment Checklist

### 6.1 Pre-Production

- [ ] All STORY-005 poison pill tests pass
- [ ] Error handlers registered in FastAPI
- [ ] Error boundaries wrap all critical widgets
- [ ] Database connection pooling configured
- [ ] Redis caching implemented for hot paths
- [ ] Retry logic added to network calls
- [ ] Null safety validated in all models
- [ ] Memory leaks checked (Dart DevTools)
- [ ] Performance profiled (Flutter DevTools)
- [ ] Security headers configured (CORS, CSP)

### 6.2 Production Environment

Current production is Kubernetes/ArgoCD, not Docker Compose. Key manifests live in `infra/k8s/production`.

Required hardening items:
- Keep production `/docs`, `/redoc`, and `/openapi.json` hidden via the environment gate and smoke checks.
- Keep `CORS_ALLOWED_ORIGINS` explicit.
- Keep the released Enclii CLI `v1.0.0-alpha.1` or newer in operator workstations; CLI use from this checkout still requires `ENCLII_PROJECT=bloom-scroll`.
- Keep `enclii.yaml` status probe scoped to the exact leaked default API base so localhost help text does not fail the production API-base assertion.

**Environment variables**:
```bash
# backend/.env.production
DATABASE_URL=postgresql+asyncpg://user:pass@prod-db:5432/bloom
REDIS_URL=redis://prod-redis:6379
SENTRY_DSN=https://your-sentry-dsn  # Error tracking
LOG_LEVEL=INFO
DEBUG=false
```

**Docker Compose production pattern (historical/local reference only)**:
```yaml
services:
  api:
    restart: always
    deploy:
      replicas: 3  # Horizontal scaling
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    restart: always
    volumes:
      - /mnt/data/postgres:/var/lib/postgresql/data

  redis:
    restart: always
    command: redis-server --appendonly yes
```

### 6.3 Monitoring Setup

- [ ] Sentry configured for error tracking
- [ ] Prometheus metrics exposed
- [ ] Grafana dashboards created
- [ ] Uptime monitoring (UptimeRobot, Pingdom)
- [ ] Log aggregation (Loki, ElasticSearch)
- [ ] Alerts configured (PagerDuty, email)

---

## 7. Quick Wins (Start Here)

### Priority 1 (Critical - Do Now)
1. ✅ **Add error handlers to FastAPI** (`error_handlers.py` created)
2. ✅ **Add ErrorBoundary to Flutter** (`error_boundary.dart` created)
3. ✅ **Repair poison pill tests**
4. 🛠️ **Hide production API docs** by rolling out the staged `ENV=production`
5. **Add validation to all API endpoints** (Pydantic models)

### Priority 2 (High - This Week)
6. **Implement retry logic** in API service (exponential backoff)
7. **Add database connection pooling** (already in schema, verify config)
8. ✅ **Add health check endpoint** (`/health`)
9. **Profile Flutter performance** (DevTools)
10. **Add null checks to all `fromJson` methods**

### Priority 3 (Medium - This Month)
11. **Add Redis caching** for frequent queries
12. **Implement rate limiting** (slowapi)
13. **Add integration tests** (end-to-end feed flow)
14. **Set up Sentry** for production error tracking
15. **Load test with Locust** (simulate 100+ concurrent users)

---

## 8. Common Failure Modes & Fixes

| Failure Mode | Symptom | Fix |
|-------------|---------|-----|
| **Database timeout** | 503 errors, slow responses | Add connection pooling, retry logic |
| **Memory leak (Flutter)** | App crashes after extended use | Profile with DevTools, dispose controllers |
| **Null pointer (Dart)** | Red screen, "null check operator" | Add `?` operators, default values |
| **Large image OOM** | App crashes loading images | Resize images, limit cache size |
| **Slow vector search** | Feed takes >2s to load | Use existing HNSW index from migration, reduce candidate pool, or push distance filtering into pgvector query |
| **API rate limits** | 429 errors | Implement backoff, cache responses |
| **Invalid JSON** | Parse errors | Validate schemas, add error cards |

---

## Summary

**To stabilize your app immediately:**

1. Run the poison pill tests I created
2. Integrate the error handlers into your FastAPI app
3. Wrap your Flutter app in the ErrorBoundary widget
4. Add retry logic to network calls
5. Profile performance with DevTools

**Then progressively add:**
- Health checks
- Monitoring (Sentry)
- Load testing
- Caching layer

The app is live in production alpha, but stabilization is not complete. Verify the production docs rollout first; then expand frontend coverage, monitoring, and load testing.
