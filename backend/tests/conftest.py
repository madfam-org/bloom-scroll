"""
Pytest configuration and fixtures for Bloom Scroll backend tests.
"""

import asyncio
from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

# Test database URL - uses test database
TEST_DATABASE_URL = "postgresql+asyncpg://bloom:bloom_dev@localhost:5434/bloom_test"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
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

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session
        await session.rollback()

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client."""
    # Import here to avoid circular imports
    from app.main import app

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_feed_data() -> dict:
    """Sample feed data for testing."""
    return {
        "name": "Test Feed",
        "url": "https://example.com/feed.xml",
        "perspective": "technology",
        "update_frequency": "daily",
    }


@pytest.fixture
def sample_article_data() -> dict:
    """Sample article data for testing."""
    return {
        "title": "Test Article",
        "url": "https://example.com/article",
        "content": "This is test content for the article.",
        "published_at": "2025-01-01T00:00:00Z",
        "source": "Test Source",
    }
