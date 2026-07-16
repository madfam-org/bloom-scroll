"""The Bloom Algorithm - Serendipity-based feed generation."""

import logging
from typing import cast
from uuid import UUID

from sqlalchemy import and_, func, select
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
        exclude_ids: list[str] | None = None,
    ) -> list[BloomCard]:
        """
        Generate a feed with serendipity scoring.

        Args:
            session: Database session
            user_context_ids: IDs of recently viewed cards (last 5)
            limit: Number of cards to return
            exclude_ids: IDs the client has already been served today;
                these are never returned again (fixes duplicate pages)

        Returns:
            List of BloomCards ordered by serendipity score
        """
        # Cards used as context are by definition already read: exclude them
        # from candidates along with anything the client has already seen.
        exclude_uuids = self._to_uuid_set(exclude_ids, user_context_ids)

        # If no user context, just return recent cards
        if not user_context_ids:
            return await self._get_recent_cards(session, limit, exclude_uuids)

        # Get user context embeddings
        context_vector = await self._calculate_user_context(session, user_context_ids)
        if not context_vector or all(v == 0.0 for v in context_vector):
            logger.warning("Invalid context vector, falling back to recent cards")
            return await self._get_recent_cards(session, limit, exclude_uuids)

        # Query for cards in the serendipity zone
        cards = await self._query_serendipity_zone(
            session, context_vector, limit, exclude_uuids
        )

        # Top up with recent unseen cards when the serendipity zone alone
        # cannot fill the page (small corpus, tight zone, etc.).
        if len(cards) < limit:
            already = exclude_uuids | {cast(UUID, card.id) for card in cards}
            filler = await self._get_recent_cards(session, limit - len(cards), already)
            cards.extend(filler)

        logger.info(f"Generated feed with {len(cards)} cards using serendipity scoring")
        return cards

    @staticmethod
    def _to_uuid_set(*id_lists: list[str] | None) -> set[UUID]:
        """Merge string-id lists into a set of UUIDs, skipping invalid values."""
        merged: set[UUID] = set()
        for ids in id_lists:
            for value in ids or []:
                try:
                    merged.add(UUID(value))
                except (ValueError, AttributeError, TypeError):
                    logger.warning(f"Skipping invalid card id in exclusion list: {value!r}")
        return merged

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
        exclude_uuids: set[UUID] | None = None,
    ) -> list[BloomCard]:
        """
        Query for cards in the serendipity zone.

        The distance-band filter and ideal-distance ordering run in SQL via
        pgvector's native cosine distance, so the whole corpus is a candidate
        (previously only the ~3x-limit most recent rows were considered and
        distances were computed in Python).

        Args:
            session: Database session
            context_vector: User's context vector
            limit: Number of cards to return
            exclude_uuids: Card ids that must not be returned

        Returns:
            List of BloomCards in the serendipity zone, closest to the
            zone's midpoint first
        """
        distance = BloomCard.embedding.cosine_distance(context_vector)
        ideal_distance = (self.min_distance + self.max_distance) / 2

        stmt = (
            select(BloomCard)
            .where(
                and_(
                    BloomCard.embedding.isnot(None),
                    distance >= self.min_distance,
                    distance <= self.max_distance,
                )
            )
            .order_by(func.abs(distance - ideal_distance))
            .limit(limit)
        )
        if exclude_uuids:
            stmt = stmt.where(BloomCard.id.notin_(exclude_uuids))

        result = await session.execute(stmt)
        result_cards = list(result.scalars().all())

        logger.info(
            f"Serendipity zone ({self.min_distance} to {self.max_distance}) "
            f"returned {len(result_cards)} cards"
        )

        return result_cards

    async def _get_recent_cards(
        self,
        session: AsyncSession,
        limit: int,
        exclude_uuids: set[UUID] | None = None,
    ) -> list[BloomCard]:
        """
        Get recent cards (fallback when no user context).

        Args:
            session: Database session
            limit: Number of cards to return
            exclude_uuids: Card ids that must not be returned

        Returns:
            List of recent BloomCards
        """
        stmt = select(BloomCard).order_by(BloomCard.created_at.desc()).limit(limit)
        if exclude_uuids:
            stmt = stmt.where(BloomCard.id.notin_(exclude_uuids))
        result = await session.execute(stmt)
        return list(result.scalars().all())

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

    @staticmethod
    def interleave_sources(cards: list[BloomCard]) -> list[BloomCard]:
        """
        "Robin Hood" layout (PRD §3.3): reorder so adjacent cards differ in
        source_type whenever inventory allows, balancing image-rich and
        text-heavy content for visual rhythm. Greedy round-robin over
        source types, preserving each type's internal order; falls back to
        repeats only when a single type dominates the remainder.
        """
        if len(cards) < 3:
            return cards

        by_source: dict[str, list[BloomCard]] = {}
        for card in cards:
            by_source.setdefault(str(card.source_type), []).append(card)

        result: list[BloomCard] = []
        last_source: str | None = None
        while any(by_source.values()):
            # Prefer the most-stocked type that differs from the last pick.
            candidates = sorted(
                (source for source, queue in by_source.items() if queue),
                key=lambda source: -len(by_source[source]),
            )
            pick = next(
                (source for source in candidates if source != last_source),
                candidates[0],
            )
            result.append(by_source[pick].pop(0))
            last_source = pick

        return result

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
        card_embedding = cast(list[float] | None, card.embedding)
        if not context_vector or not card_embedding:
            return "RECENT"

        # Calculate distance
        distance = self.nlp.calculate_cosine_distance(card_embedding, context_vector)

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
