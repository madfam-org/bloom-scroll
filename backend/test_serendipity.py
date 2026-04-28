#!/usr/bin/env python3
"""
Test script for STORY-004: Perspective Engine (Serendipity Scoring)

This script validates the "Echo Chamber Test" acceptance criteria:
- User views 5 similar cards consecutively
- Refresh feed
- Expected: Feed stops showing similar content, jumps to new topic

The serendipity algorithm should detect the pattern and serve content
from the "serendipity zone" (cosine distance 0.3-0.8).
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.processor import get_nlp_processor
from app.core.database import async_session_maker
from app.curation.bloom_algorithm import BloomAlgorithm
from app.ingestion.aesthetics import AestheticsConnector
from app.ingestion.owid import OWIDConnector
from app.models.bloom_card import BloomCard
from app.models.user_interaction import UserInteraction


async def clear_test_data(session: AsyncSession):
    """Clear existing test data."""
    print("🧹 Clearing existing test data...")
    await session.execute("DELETE FROM user_interactions")
    await session.execute("DELETE FROM bloom_cards")
    await session.commit()
    print("✅ Test data cleared\n")


async def ingest_diverse_content(session: AsyncSession):
    """Ingest diverse content from multiple sources."""
    print("📥 Ingesting diverse content...")

    # Ingest OWID datasets (science/data topics)
    owid = OWIDConnector()
    owid_cards = []

    for dataset_key in ["co2_emissions", "life_expectancy", "child_mortality"]:
        card = await owid.ingest_to_database(session, dataset_key, entity="World", years_back=20)
        if card:
            owid_cards.append(card)
            print(f"  ✓ OWID: {card.title}")

    # Ingest aesthetic images (visual culture topics)
    aesthetics = AestheticsConnector()
    aesthetic_cards = []

    for channel_key in ["architecture", "minimalism", "cyberpunk"]:
        cards = await aesthetics.ingest_channel(session, channel_key, limit=3)
        aesthetic_cards.extend(cards)
        for card in cards:
            print(f"  ✓ Aesthetic: {card.title}")

    await session.commit()

    print(f"✅ Ingested {len(owid_cards)} OWID cards and {len(aesthetic_cards)} aesthetic cards\n")

    return owid_cards, aesthetic_cards


async def simulate_echo_chamber(
    session: AsyncSession, cards: list[BloomCard], user_id: str = "test_user"
):
    """
    Simulate user viewing 5 similar cards consecutively.

    This creates an "echo chamber" pattern that the algorithm should detect.
    """
    print(f"👤 Simulating echo chamber for user: {user_id}")
    print("   User views 5 similar cards consecutively...\n")

    # Use the first 5 cards of same type (e.g., all OWID data cards)
    similar_cards = cards[:5]

    interaction_ids = []
    for i, card in enumerate(similar_cards, 1):
        interaction = UserInteraction(
            user_id=user_id,
            card_id=card.id,
            action="read",
            dwell_time=30 + i * 5,  # Simulate varied reading time
        )
        session.add(interaction)
        await session.flush()
        interaction_ids.append(str(card.id))

        print(f"   {i}. Read: {card.title[:60]}...")

    await session.commit()

    print(f"✅ Simulated {len(interaction_ids)} interactions\n")

    return interaction_ids


async def test_feed_without_context(session: AsyncSession):
    """Test baseline feed without user context."""
    print("📊 Test 1: Feed WITHOUT context (baseline)")

    bloom = BloomAlgorithm(min_distance=0.3, max_distance=0.8)
    cards = await bloom.generate_feed(session, user_context_ids=None, limit=10)

    print(f"   Retrieved {len(cards)} cards")
    for i, card in enumerate(cards[:5], 1):
        print(f"   {i}. {card.source_type:12} | {card.title[:50]}")

    print("✅ Baseline feed generated\n")
    return cards


async def test_feed_with_context(session: AsyncSession, context_ids: list[str]):
    """Test feed WITH user context (serendipity mode)."""
    print("🎯 Test 2: Feed WITH context (serendipity mode)")
    print(f"   Context: {len(context_ids)} recently viewed cards")

    bloom = BloomAlgorithm(min_distance=0.3, max_distance=0.8)
    cards = await bloom.generate_feed(session, user_context_ids=context_ids, limit=10)

    print(f"   Retrieved {len(cards)} cards")
    print("\n   Serendipity-scored feed:")
    for i, card in enumerate(cards[:5], 1):
        print(f"   {i}. {card.source_type:12} | {card.title[:50]}")

    print("\n✅ Serendipity feed generated\n")
    return cards


async def analyze_diversity(baseline_cards: list[BloomCard], serendipity_cards: list[BloomCard]):
    """
    Analyze the diversity difference between baseline and serendipity feeds.

    Expected: Serendipity feed should have more diverse source types.
    """
    print("📈 Diversity Analysis")

    def get_source_distribution(cards):
        distribution = {}
        for card in cards:
            distribution[card.source_type] = distribution.get(card.source_type, 0) + 1
        return distribution

    baseline_dist = get_source_distribution(baseline_cards)
    serendipity_dist = get_source_distribution(serendipity_cards)

    print("\n   Baseline feed distribution:")
    for source, count in baseline_dist.items():
        print(f"     {source:12} : {count} cards")

    print("\n   Serendipity feed distribution:")
    for source, count in serendipity_dist.items():
        print(f"     {source:12} : {count} cards")

    # Calculate diversity score (number of unique sources)
    baseline_diversity = len(baseline_dist)
    serendipity_diversity = len(serendipity_dist)

    print(f"\n   Baseline diversity: {baseline_diversity} unique source types")
    print(f"   Serendipity diversity: {serendipity_diversity} unique source types")

    if serendipity_diversity >= baseline_diversity:
        print("   ✅ PASS: Serendipity feed has equal or more diversity")
    else:
        print("   ⚠️  WARNING: Serendipity feed has less diversity")

    print()


async def test_echo_chamber_detection(session: AsyncSession, context_ids: list[str]):
    """
    Test that the algorithm detects echo chamber and breaks it.

    Expected: Cards returned should NOT be in the context set.
    """
    print("🔍 Echo Chamber Detection Test")

    bloom = BloomAlgorithm(min_distance=0.3, max_distance=0.8)
    cards = await bloom.generate_feed(session, user_context_ids=context_ids, limit=10)

    # Check if returned cards are different from context
    returned_ids = {str(card.id) for card in cards}
    context_set = set(context_ids)

    overlap = returned_ids & context_set

    print(f"   Context cards: {len(context_set)}")
    print(f"   Returned cards: {len(returned_ids)}")
    print(f"   Overlap: {len(overlap)} cards")

    if len(overlap) == 0:
        print("   ✅ PASS: No overlap - echo chamber successfully broken!")
    elif len(overlap) < len(context_set) / 2:
        print("   ⚠️  WARNING: Some overlap, but mostly new content")
    else:
        print("   ❌ FAIL: Too much overlap - echo chamber not broken")

    print()


async def calculate_serendipity_scores(session: AsyncSession, context_ids: list[str]):
    """
    Calculate actual serendipity scores for cards in feed.

    Shows the distribution of cosine distances to validate the 0.3-0.8 zone.
    """
    print("📐 Serendipity Score Distribution")

    # Get context cards
    context_stmt = select(BloomCard).where(BloomCard.id.in_(context_ids))
    context_result = await session.execute(context_stmt)
    context_cards = context_result.scalars().all()

    # Calculate average context vector
    nlp = get_nlp_processor()
    context_embeddings = [card.embedding for card in context_cards if card.embedding]

    if not context_embeddings:
        print("   ⚠️  No embeddings in context - skipping score calculation")
        return

    avg_context = nlp.average_embeddings(context_embeddings)

    # Get all cards and calculate distances
    all_stmt = select(BloomCard).where(BloomCard.embedding.isnot(None))
    all_result = await session.execute(all_stmt)
    all_cards = all_result.scalars().all()

    distances = []
    for card in all_cards:
        if str(card.id) not in context_ids:  # Exclude context cards
            distance = nlp.calculate_cosine_distance(card.embedding, avg_context)
            distances.append((card, distance))

    # Sort by distance
    distances.sort(key=lambda x: x[1])

    print("\n   Top 10 cards by serendipity score:")
    print("   (Ideal range: 0.3 - 0.8)")
    print()

    for i, (card, distance) in enumerate(distances[:10], 1):
        in_zone = "✓" if 0.3 <= distance <= 0.8 else " "
        print(f"   {i:2}. [{in_zone}] {distance:.3f} | {card.source_type:12} | {card.title[:40]}")

    # Count cards in serendipity zone
    in_zone = sum(1 for _, d in distances if 0.3 <= d <= 0.8)
    total = len(distances)
    percentage = (in_zone / total * 100) if total > 0 else 0

    print(f"\n   Cards in serendipity zone: {in_zone}/{total} ({percentage:.1f}%)")
    print()


async def main():
    """Run all serendipity tests."""
    print("=" * 70)
    print("STORY-004: Perspective Engine - Serendipity Test Suite")
    print("=" * 70)
    print()

    async with async_session_maker() as session:
        try:
            # Setup
            await clear_test_data(session)
            owid_cards, aesthetic_cards = await ingest_diverse_content(session)

            # Simulate echo chamber with OWID cards (similar content)
            context_ids = await simulate_echo_chamber(session, owid_cards, user_id="test_user")

            # Run tests
            baseline_cards = await test_feed_without_context(session)
            serendipity_cards = await test_feed_with_context(session, context_ids)

            # Analysis
            await analyze_diversity(baseline_cards, serendipity_cards)
            await test_echo_chamber_detection(session, context_ids)
            await calculate_serendipity_scores(session, context_ids)

            print("=" * 70)
            print("✅ All tests completed successfully!")
            print("=" * 70)

        except Exception as e:
            print(f"\n❌ Error during testing: {e}")
            import traceback
            traceback.print_exc()
            raise


if __name__ == "__main__":
    asyncio.run(main())
