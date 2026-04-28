"""Pydantic schemas for BloomCard."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class BloomCardBase(BaseModel):
    """Base schema for BloomCard."""

    source_type: str = Field(..., description="OWID, OPENALEX, CARI, NEOCITIES, etc.")
    title: str = Field(..., min_length=1, max_length=500)
    summary: str | None = Field(None, description="LLM-generated summary")
    original_url: str = Field(..., description="Source URL")
    data_payload: dict[str, Any] = Field(..., description="Polymorphic content data")


class BloomCardCreate(BloomCardBase):
    """Schema for creating a new BloomCard."""

    bias_score: float | None = Field(None, ge=0.0, le=1.0)
    constructiveness_score: float | None = Field(None, ge=0.0, le=100.0)
    blindspot_tags: list[str] | None = None
    embedding: list[float] | None = Field(
        None,
        description="384-dimensional SBERT embedding",
    )


class BloomCardResponse(BloomCardBase):
    """Schema for BloomCard API responses."""

    id: UUID
    bias_score: float | None = None
    constructiveness_score: float | None = None
    blindspot_tags: list[str] | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class OWIDDataPayload(BaseModel):
    """OWID-specific data payload structure."""

    chart_type: str = Field(default="line", description="line, bar, scatter, etc.")
    years: list[int] = Field(..., description="X-axis data")
    values: list[float] = Field(..., description="Y-axis data")
    unit: str = Field(..., description="Unit of measurement")
    indicator: str = Field(..., description="What is being measured")
    entity: str = Field(default="World", description="Country/region name")
