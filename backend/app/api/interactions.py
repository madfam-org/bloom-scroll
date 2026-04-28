"""User interaction tracking endpoints."""

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user_interaction import UserInteraction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/interactions", tags=["interactions"])


class InteractionCreate(BaseModel):
    """Schema for creating user interaction."""
    user_id: str
    card_id: str
    action: str  # view, read, skip, save
    dwell_time: int | None = None


@router.post("/track")
async def track_interaction(
    interaction: InteractionCreate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Track a user interaction with a card.

    Args:
        interaction: Interaction data
        db: Database session

    Returns:
        Confirmation message
    """
    user_interaction = UserInteraction(
        user_id=interaction.user_id,
        card_id=interaction.card_id,
        action=interaction.action,
        dwell_time=interaction.dwell_time,
    )

    db.add(user_interaction)
    await db.commit()

    return {"message": "Interaction tracked", "id": str(user_interaction.id)}


@router.get("/recent/{user_id}")
async def get_recent_interactions(
    user_id: str,
    limit: int = 5,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get user's recent interactions for context building.

    Args:
        user_id: User identifier
        limit: Number of recent interactions (default: 5)
        db: Database session

    Returns:
        List of recent card IDs
    """
    stmt = (
        select(UserInteraction.card_id)
        .where(
            and_(
                UserInteraction.user_id == user_id,
                UserInteraction.action.in_(["view", "read"]),  # Only meaningful interactions
            )
        )
        .order_by(UserInteraction.created_at.desc())
        .limit(limit)
    )

    result = await db.execute(stmt)
    card_ids = [str(row[0]) for row in result.fetchall()]

    return {
        "user_id": user_id,
        "recent_card_ids": card_ids,
        "count": len(card_ids),
    }
