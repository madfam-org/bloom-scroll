"""
Test script for STORY-001: Infrastructure & OWID Ingestion

This script tests the acceptance criteria:
1. Database connection works
2. OWID ingestion creates a card
3. Data payload is valid JSON
"""

import asyncio
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.ingestion.owid import OWIDConnector
from app.models.bloom_card import BloomCard


async def test_story_001():
    """Run acceptance tests for STORY-001."""

    print("=" * 60)
    print("STORY-001 Acceptance Tests")
    print("=" * 60)

    # Database connection
    DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/bloom_scroll"

    print("\n1. Testing database connection...")
    try:
        engine = create_async_engine(DATABASE_URL, echo=False)
        AsyncSessionLocal = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        async with AsyncSessionLocal() as session:
            # Test connection
            await session.execute(select(BloomCard).limit(1))
            print("   ✓ Database connection successful")
    except Exception as e:
        print(f"   ✗ Database connection failed: {e}")
        return False

    # Test OWID ingestion
    print("\n2. Testing OWID ingestion...")
    try:
        connector = OWIDConnector()

        async with AsyncSessionLocal() as session:
            # Count cards before
            result_before = await session.execute(select(BloomCard))
            count_before = len(result_before.scalars().all())
            print(f"   Cards before ingestion: {count_before}")

            # Ingest CO2 data
            card = await connector.ingest_to_database(
                session,
                dataset_key="co2_emissions",
                entity="World",
                years_back=20
            )

            if card:
                print(f"   ✓ Card created: {card.id}")
                print(f"   ✓ Title: {card.title}")
                print(f"   ✓ Source: {card.source_type}")

                # Commit the transaction
                await session.commit()
            else:
                print("   ✗ Failed to create card")
                return False
    except Exception as e:
        print(f"   ✗ OWID ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Verify data payload
    print("\n3. Testing data payload structure...")
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(BloomCard).where(BloomCard.source_type == "OWID").limit(1)
            )
            card = result.scalar_one()

            payload = card.data_payload

            # Check required fields
            required_fields = ["years", "values", "unit", "indicator"]
            for field in required_fields:
                if field not in payload:
                    print(f"   ✗ Missing field: {field}")
                    return False

            print("   ✓ Data payload is valid JSON")
            print(f"   ✓ Years: {len(payload['years'])} data points")
            print(f"   ✓ Indicator: {payload['indicator']}")
            print(f"   ✓ Unit: {payload['unit']}")
            print(f"   ✓ Sample data: {payload['years'][:3]} -> {payload['values'][:3]}")

    except Exception as e:
        print(f"   ✗ Data payload validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("All acceptance criteria passed! ✓")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = asyncio.run(test_story_001())
    sys.exit(0 if success else 1)
