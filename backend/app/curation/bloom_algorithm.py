"""The Bloom Algorithm - Serendipity-based feed generation."""

import logging

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.processor import get_nlp_processor
from app.models.bloom_card import BloomCard

logger = logging.getLogger(__name__)


class BloomAlgorithm:
    """
    Implements the "Serendipity Zone" algorithm.

    The Goldilocks principle: Content should be different enough to be novel,
    but close enough to be understood.

    Distance zones:
    - < 0.3: Echo chamber (too similar)
    - 0.3 to 0.8: Serendipity zone (GOLDILOCKS!)
    - > 0.8: Noise (too irrelevant)
    """

    def __init__(
        self,
        min_distance: float = 0.3,
        max_distance: float = 0.8,
        min_quality: float = 70.0,
    ):
        """
        Initialize the algorithm.

        Args:
            min_distance: Minimum cosine distance to avoid echo chamber
            max_distance: Maximum cosine distance to avoid irrelevance
            min_quality: Minimum constructiveness score (0-100)
        """
        self.min_distance = min_distance
        self.max_distance = max_distance
        self.min_quality = min_quality
        self.nlp = get_nlp_processor()

    async def generate_feed(
        self,
        session: AsyncSession,
        user_context_ids: list[str] | None = None,
        limit: int = 20,
    ) -> list[BloomCard]:
        """
        Generate a feed with serendipity scoring.

        Args:
            session: Database session
            user_context_ids: IDs of recently viewed cards (last 5)
            limit: Number of cards to return

        Returns:
            List of BloomCards ordered by serendipity score
        """
        # If no user context, just return recent cards
        if not user_context_ids:
            return await self._get_recent_cards(session, limit)

        # Get user context embeddings
        context_vector = await self._calculate_user_context(session, user_context_ids)
        if not context_vector or all(v == 0.0 for v in context_vector):
            logger.warning("Invalid context vector, falling back to recent cards")
            return await self._get_recent_cards(session, limit)

        # Query for cards in the serendipity zone
        cards = await self._query_serendipity_zone(session, context_vector, limit)

        logger.info(f"Generated feed with {len(cards)} cards using serendipity scoring")
        return cards

    async def _calculate_user_context(
        self,
        session: AsyncSession,
        card_ids: list[str],
    ) -> list[float]:
        """
        Calculate the user's context vector from their recent reads.

        Args:
            session: Database session
            card_ids: IDs of recently viewed cards

        Returns:
            Average embedding vector representing user context
        """
        # Fetch embeddings for the cards
        stmt = select(BloomCard.embedding).where(
            and_(
                BloomCard.id.in_(card_ids),
                BloomCard.embedding.isnot(None),
            )
        )
        result = await session.execute(stmt)
        embeddings = [row[0] for row in result.fetchall() if row[0]]

        if not embeddings:
            return [0.0] * 384

        # Calculate average (context vector)
        context_vector = self.nlp.calculate_context_vector(embeddings)
        return context_vector

    async def _query_serendipity_zone(
        self,
        session: AsyncSession,
        context_vector: list[float],
        limit: int,
    ) -> list[BloomCard]:
        """
        Query for cards in the serendipity zone.

        Uses pgvector for efficient similarity search.

        Args:
            session: Database session
            context_vector: User's context vector
            limit: Number of cards to return

        Returns:
            List of BloomCards in the serendipity zone
        """
        # Convert context vector to string for pgvector
        # pgvector uses cosine distance natively

        # Query cards with pgvector cosine distance
        # Note: We want distance between min_distance and max_distance
        stmt = (
            select(BloomCard)
            .where(
                and_(
                    BloomCard.embedding.isnot(None),
                    # High quality filter (if constructiveness_score exists)
                    # For now, we'll just get all cards and filter in Python
                )
            )
            .order_by(BloomCard.created_at.desc())
            .limit(limit * 3)  # Get more candidates for filtering
        )

        result = await session.execute(stmt)
        all_cards = result.scalars().all()

        # Filter by serendipity zone in Python
        # (pgvector WHERE clause would be complex for range queries)
        serendipity_cards = []

        for card in all_cards:
            if not card.embedding:
                continue

            # Calculate distance
            distance = self.nlp.calculate_cosine_distance(card.embedding, context_vector)

            # Check if in serendipity zone
            if self.min_distance <= distance <= self.max_distance:
                serendipity_cards.append((distance, card))

        # Sort by distance (prefer middle of serendipity zone)
        # Ideal distance is midpoint: (min + max) / 2
        ideal_distance = (self.min_distance + self.max_distance) / 2
        serendipity_cards.sort(key=lambda x: abs(x[0] - ideal_distance))

        # Return just the cards (without distances)
        result_cards = [card for _, card in serendipity_cards[:limit]]

        logger.info(
            f"Found {len(serendipity_cards)} cards in serendipity zone "
            f"({self.min_distance} to {self.max_distance}), returning {len(result_cards)}"
        )

        return result_cards

    async def _get_recent_cards(
        self,
        session: AsyncSession,
        limit: int,
    ) -> list[BloomCard]:
        """
        Get recent cards (fallback when no user context).

        Args:
            session: Database session
            limit: Number of cards to return

        Returns:
            List of recent BloomCards
        """
        stmt = select(BloomCard).order_by(BloomCard.created_at.desc()).limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()

    def calculate_serendipity_score(
        self,
        card_embedding: list[float],
        context_vector: list[float],
    ) -> float:
        """
        Calculate serendipity score for a card.

        Score formula: S = (1 - |distance - ideal_distance|)
        Where ideal_distance is the midpoint of the serendipity zone.

        Args:
            card_embedding: Card's embedding vector
            context_vector: User's context vector

        Returns:
            Serendipity score from 0.0 to 1.0 (higher = better)
        """
        distance = self.nlp.calculate_cosine_distance(card_embedding, context_vector)

        # Check if in serendipity zone
        if distance < self.min_distance or distance > self.max_distance:
            return 0.0

        # Calculate score based on proximity to ideal distance
        ideal_distance = (self.min_distance + self.max_distance) / 2
        deviation = abs(distance - ideal_distance)
        max_deviation = (self.max_distance - self.min_distance) / 2

        score = 1.0 - (deviation / max_deviation)
        return max(0.0, min(1.0, score))

    def calculate_reason_tag(
        self,
        card: BloomCard,
        context_vector: list[float] | None = None,
    ) -> str:
        """
        Calculate reason tag explaining why this card was recommended.

        Args:
            card: The BloomCard
            context_vector: User's context vector (if available)

        Returns:
            Reason tag string (e.g., "BLINDSPOT_BREAKER", "DEEP_DIVE")
        """
        # No context = recent/popular
        if not context_vector or not card.embedding:
            return "RECENT"

        # Calculate distance
        distance = self.nlp.calculate_cosine_distance(card.embedding, context_vector)

        # Check if there are blindspot tags
        if card.blindspot_tags and len(card.blindspot_tags) > 0:
            return "BLINDSPOT_BREAKER"

        # High distance = exploring new territory
        if distance > 0.6:
            return "EXPLORE"

        # Medium distance = related but novel
        if distance > 0.4:
            return "PERSPECTIVE_SHIFT"

        # Low distance = deep dive into familiar topic
        if distance < 0.4:
            return "DEEP_DIVE"

        return "SERENDIPITY"
