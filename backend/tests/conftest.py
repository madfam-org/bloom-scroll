"""
Pytest configuration and fixtures for Bloom Scroll backend tests.
"""

import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import Any, cast

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Test database URL - uses test database
TEST_DATABASE_URL = "postgresql+asyncpg://bloom:bloom_dev@localhost:5434/bloom_test"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
    )

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session
        await session.rollback()

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client."""
    # Import here to avoid circular imports
    from app.core.database import get_db
    from app.main import app

    class _FakeResult:
        def __init__(self, scalar_value: Any = None):
            self._scalar_value = scalar_value

        def scalar(self) -> Any:
            return self._scalar_value

        def scalars(self) -> "_FakeResult":
            return self

        def all(self) -> list[Any]:
            return []

        def fetchall(self) -> list[Any]:
            return []

    class _FakeDBSession:
        async def execute(self, statement: Any) -> _FakeResult:
            query = str(statement)
            if "SELECT 1" in query:
                return _FakeResult(1)
            if "embedding IS NOT NULL" in query:
                return _FakeResult(0)
            if "COUNT(*) FROM bloom_cards" in query:
                return _FakeResult(0)
            return _FakeResult(None)

    async def override_get_db() -> AsyncGenerator[_FakeDBSession, None]:
        yield _FakeDBSession()

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=cast(Any, app))

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def sample_feed_data() -> dict[str, str]:
    """Sample feed data for testing."""
    return {
        "name": "Test Feed",
        "url": "https://example.com/feed.xml",
        "perspective": "technology",
        "update_frequency": "daily",
    }


@pytest.fixture
def sample_article_data() -> dict[str, str]:
    """Sample article data for testing."""
    return {
        "title": "Test Article",
        "url": "https://example.com/article",
        "content": "This is test content for the article.",
        "published_at": "2025-01-01T00:00:00Z",
        "source": "Test Source",
    }
