"""User interaction tracking model."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class UserInteraction(Base):
    """
    Track user interactions with bloom cards.

    Used for serendipity scoring (recent context calculation).
    """

    __tablename__ = "user_interactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        String(255),
        nullable=False,
        index=True,
        comment="User identifier (can be session ID)",
    )
    card_id = Column(UUID(as_uuid=True), nullable=False, index=True, comment="BloomCard ID")
    action = Column(String(50), nullable=False, comment="view, read, skip, save")
    dwell_time = Column(Integer, nullable=True, comment="Time spent on card in seconds")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<UserInteraction(user={self.user_id}, card={self.card_id}, action={self.action})>"
