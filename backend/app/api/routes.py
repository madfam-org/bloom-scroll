"""Main API router combining all endpoint modules."""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import ingestion, interactions
from app.core.database import get_db
from app.curation.bloom_algorithm import BloomAlgorithm
from app.models.bloom_card import BloomCard

logger = logging.getLogger(__name__)

router = APIRouter()

# Include sub-routers
router.include_router(ingestion.router)
router.include_router(interactions.router)

# STORY-007: The Finite Feed
# Hard-coded daily limit to prevent infinite scrolling
DAILY_LIMIT = 20


@router.get("/feed")
async def get_feed(
    user_context: list[str] | None = Query(
        None,
        description="IDs of recently viewed cards (for serendipity scoring)"
    ),
    exclude_ids: list[str] | None = Query(
        None,
        description="IDs of cards already served today; they will not be returned again"
    ),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    read_count: int = Query(0, ge=0, description="Number of cards already read today"),
    limit: int = Query(10, ge=1, le=20, description="Cards per page (max 20)"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Generate a bloom feed session with serendipity scoring and finite pagination.

    STORY-007: The Finite Feed
    - Daily limit of 20 cards to prevent infinite scrolling
    - Returns completion object when limit reached
    - Pagination enforces "The End" as the product

    Returns a finite feed optimized for:
    - High serendipity score (avoids echo chambers)
    - Source diversity
    - Visual rhythm

    If user_context is provided (IDs of last 5 viewed cards), the algorithm
    will return cards in the "Serendipity Zone": different enough to be novel,
    close enough to be understood.

    Args:
        user_context: Optional list of recently viewed card IDs
        page: Page number (1-indexed)
        read_count: Number of cards already read today (for limit enforcement)
        limit: Cards per page (default: 10, max: 20)
        db: Database session

    Returns:
        Feed response with cards, pagination metadata, and optional completion object
    """
    # Enforce daily limit
    remaining_cards = DAILY_LIMIT - read_count

    # If already at or over limit, return completion immediately
    if remaining_cards <= 0:
        return {
            "cards": [],
            "pagination": {
                "page": page,
                "limit": limit,
                "has_next_page": False,
                "total_read_today": read_count,
                "daily_limit": DAILY_LIMIT,
            },
            "completion": {
                "type": "COMPLETION",
                "message": "The Garden is Watered.",
                "subtitle": "You've reached today's limit. Return tomorrow for fresh blooms.",
                "stats": {
                    "read_count": read_count,
                    "daily_limit": DAILY_LIMIT,
                },
            },
        }

    # Validate user_context UUIDs if provided
    if user_context:
        try:
            for card_id in user_context:
                UUID(card_id)  # Validate UUID format
        except ValueError as e:
            logger.warning(f"Invalid UUID in user_context: {e}")
            raise HTTPException(
                status_code=422,
                detail=f"Invalid UUID format in user_context: {str(e)}"
            )

    # Validate exclude_ids UUIDs if provided
    if exclude_ids:
        try:
            for card_id in exclude_ids:
                UUID(card_id)
        except ValueError as e:
            logger.warning(f"Invalid UUID in exclude_ids: {e}")
            raise HTTPException(
                status_code=422,
                detail=f"Invalid UUID format in exclude_ids: {str(e)}"
            )

    # Adjust limit to not exceed daily cap
    effective_limit = min(limit, remaining_cards)

    # Use Bloom Algorithm for serendipity scoring
    bloom = BloomAlgorithm(
        min_distance=0.3,  # Minimum distance to avoid echo chamber
        max_distance=0.8,  # Maximum distance to avoid irrelevance
    )

    # Everything the client has already seen today: never serve it again.
    seen_ids = {*(exclude_ids or []), *(user_context or [])}

    # Try serendipity algorithm, fall back to recent cards on failure
    try:
        cards = await bloom.generate_feed(
            session=db,
            user_context_ids=user_context,
            limit=effective_limit,
            exclude_ids=list(seen_ids),
        )

        # Calculate context vector for reason tag generation
        context_vector = None
        if user_context:
            context_vector = await bloom._calculate_user_context(db, user_context)

        logger.info(f"Generated {len(cards)} cards with serendipity scoring")

    except Exception as e:
        # Graceful degradation: Return recent cards if algorithm fails
        logger.error(f"Bloom algorithm failed, falling back to recent cards: {e}")

        fallback_stmt = (
            select(BloomCard)
            .order_by(BloomCard.created_at.desc())
            .limit(effective_limit)
        )
        if seen_ids:
            fallback_stmt = fallback_stmt.where(
                BloomCard.id.notin_({UUID(v) for v in seen_ids})
            )
        result = await db.execute(fallback_stmt)
        cards = list(result.scalars().all())
        context_vector = None

        logger.warning(f"Fallback: Returned {len(cards)} recent cards")

    # "Robin Hood" visual rhythm: avoid same-source neighbors (PRD §3.3).
    cards = BloomAlgorithm.interleave_sources(cards)

    # Convert cards to dict with perspective metadata
    cards_data = []
    for card in cards:
        try:
            # Calculate reason tag based on serendipity context
            reason_tag = (
                bloom.calculate_reason_tag(card, context_vector)
                if context_vector
                else "RECENT"
            )
            cards_data.append(card.to_dict(include_meta=True, reason_tag=reason_tag))
        except Exception as e:
            # If single card conversion fails, skip it but log error
            logger.error(f"Failed to convert card {card.id}: {e}")
            continue

    # Calculate new read count
    new_read_count = read_count + len(cards_data)

    # A next page exists only when unseen cards actually remain AND the
    # daily limit has not been reached. Previously this was derived from
    # read_count alone, which advertised pages that re-served duplicates.
    unseen_remaining = 0
    try:
        served_ids = seen_ids | {card["id"] for card in cards_data}
        count_stmt = select(func.count()).select_from(BloomCard)
        if served_ids:
            count_stmt = count_stmt.where(
                BloomCard.id.notin_({UUID(v) for v in served_ids})
            )
        unseen_remaining = (await db.execute(count_stmt)).scalar() or 0
    except Exception as e:
        logger.error(f"Unseen-card count failed, assuming none remain: {e}")

    has_next_page = unseen_remaining > 0 and new_read_count < DAILY_LIMIT

    response: dict[str, Any] = {
        "cards": cards_data,
        "pagination": {
            "page": page,
            "limit": effective_limit,
            "has_next_page": has_next_page,
            "total_read_today": new_read_count,
            "daily_limit": DAILY_LIMIT,
        },
        "serendipity_enabled": bool(user_context),
    }

    # Add completion object if we've reached the limit
    if not has_next_page:
        response["completion"] = {
            "type": "COMPLETION",
            "message": "The Garden is Watered.",
            "subtitle": "You've reached today's limit. Return tomorrow for fresh blooms.",
            "stats": {
                "read_count": new_read_count,
                "daily_limit": DAILY_LIMIT,
            },
        }

    return response


@router.get("/perspective/{card_id}")
async def get_perspective(
    card_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get the perspective dashboard for a specific card (PRD §4.2).

    Returns measured scores only (score_provenance gate, audit D5), the
    nearest OWID data card as "The Data Layer" context, a topical-cluster
    summary as a source-diversity signal, and source attribution.
    """
    from urllib.parse import urlparse

    try:
        card_uuid = UUID(card_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="card_id must be a UUID")

    result = await db.execute(select(BloomCard).where(BloomCard.id == card_uuid))
    cards = result.scalars().all()
    if not cards:
        raise HTTPException(status_code=404, detail="Card not found")
    card = cards[0]

    measured = card.score_provenance is not None
    response: dict[str, Any] = {
        "card_id": str(card.id),
        "title": card.title,
        "source_type": card.source_type,
        "scores": {
            "bias_score": card.bias_score if measured else None,
            "constructiveness_score": card.constructiveness_score if measured else None,
            "blindspot_tags": (card.blindspot_tags or []) if measured else [],
            "score_provenance": card.score_provenance,
        },
        "source": {
            "original_url": card.original_url,
            "domain": urlparse(str(card.original_url)).netloc or None,
        },
        "data_context": None,
        "topic_cluster": None,
    }

    card_embedding = card.embedding
    if card_embedding is None:
        return response

    # "The Data Layer": the semantically nearest OWID data card, so readers
    # can check a story against ground-truth statistics (factfulness v1 —
    # retrieval only, no automated verdicts).
    try:
        distance = BloomCard.embedding.cosine_distance(card_embedding)
        stmt = (
            select(BloomCard)
            .where(
                BloomCard.source_type == "OWID",
                BloomCard.id != card.id,
                BloomCard.embedding.isnot(None),
            )
            .order_by(distance)
            .limit(1)
        )
        nearest = (await db.execute(stmt)).scalars().all()
        if nearest:
            data_card = nearest[0]
            response["data_context"] = {
                "card_id": str(data_card.id),
                "title": data_card.title,
                "original_url": data_card.original_url,
                "indicator": dict(data_card.data_payload or {}).get("indicator"),
            }
    except Exception as e:
        logger.warning(f"Perspective data-context lookup failed: {e}")

    # Topical cluster (blindspot v1): how many cards sit close to this one
    # and how source-diverse they are. A large single-source cluster is a
    # coverage blindspot signal.
    try:
        distance = BloomCard.embedding.cosine_distance(card_embedding)
        cluster_stmt = (
            select(BloomCard.source_type, func.count())
            .where(
                BloomCard.embedding.isnot(None),
                BloomCard.id != card.id,
                distance < 0.3,
            )
            .group_by(BloomCard.source_type)
        )
        rows = (await db.execute(cluster_stmt)).fetchall()
        if rows:
            by_source = {str(row[0]): int(row[1]) for row in rows}
            response["topic_cluster"] = {
                "size": sum(by_source.values()),
                "source_types": by_source,
                "single_source": len(by_source) == 1 and sum(by_source.values()) >= 3,
            }
    except Exception as e:
        logger.warning(f"Perspective cluster lookup failed: {e}")

    return response
