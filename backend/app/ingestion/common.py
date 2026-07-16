"""Shared ingestion helpers."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bloom_card import BloomCard

logger = logging.getLogger(__name__)


async def get_card_for_url(
    session: AsyncSession, original_url: str
) -> BloomCard | None:
    """
    Return the existing card for a source URL, if any.

    Connectors treat an existing URL as idempotent success (return the
    existing card, skip re-insertion): ingestion runs daily via CronJob
    (since 2026-07-16), and stable sources like OWID grapher URLs would
    otherwise either duplicate cards or read as failures on every run.
    """
    result = await session.execute(
        select(BloomCard).where(BloomCard.original_url == original_url).limit(1)
    )
    cards = result.scalars().all()
    return cards[0] if cards else None
