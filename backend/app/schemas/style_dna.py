"""Pydantic schemas for Outfit Events and Style DNA."""

from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


EventType = Literal["like", "dislike", "save", "skip", "wear"]


class RecordOutfitEventRequest(BaseModel):
    event_type: EventType = Field(
        ...,
        description="Type of interaction: like, dislike, save, skip, wear",
    )
    metadata: Optional[dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional event context, item tags or notes",
    )


class OutfitEventResponse(BaseModel):
    id: str
    user_id: str
    outfit_id: str
    event_type: str
    metadata: dict[str, Any] = {}
    created_at: Optional[str] = None


class StyleDnaPreferenceItem(BaseModel):
    dimension: str  # "color", "style", "category"
    name: str
    score: float


class StyleDnaAffinities(BaseModel):
    colors: dict[str, float] = {}
    categories: dict[str, float] = {}
    styles: dict[str, float] = {}


class StyleDnaResponse(BaseModel):
    total_events: int
    event_counts: dict[str, int] = {
        "like": 0,
        "dislike": 0,
        "save": 0,
        "skip": 0,
        "wear": 0,
    }
    affinities: StyleDnaAffinities
    top_preferences: list[StyleDnaPreferenceItem] = []
    avoidances: list[StyleDnaPreferenceItem] = []
    influence_cap: float = 0.08
    message: Optional[str] = None


class ResetStyleDnaResponse(BaseModel):
    success: bool
    message: str
