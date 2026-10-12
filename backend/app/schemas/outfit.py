"""Pydantic schemas for outfit generation and saved looks."""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


class GenerateOutfitsRequest(BaseModel):
    occasion: str = Field(default="casual", description="Occasion: casual, work, party, formal, festive, wedding, lounge, college")
    vibe: Optional[str] = Field(default=None, description="Aesthetic vibe: minimal, classic, bohemian, streetwear, elegant")
    season: str = Field(default="all_season", description="Seasonal filter: summer, winter, monsoon, all_season")
    wardrobe_only: bool = Field(default=True, description="Strictly wardrobe items only (no catalog items)")
    allow_one_new_item: bool = Field(default=False, description="Allow fallback with exactly one new catalog product if wardrobe lacks required slot or too few high-scoring outfits")
    budget_max: Optional[float] = Field(default=None, description="Maximum price in INR for catalog item")
    min_quality_threshold: float = Field(default=0.70, description="Minimum score threshold below which fallback can be activated")
    limit: int = Field(default=6, ge=1, le=20, description="Maximum number of diversified outfits to generate")


class OutfitSlotItem(BaseModel):
    slot: str
    source_type: str = "wardrobe"  # "wardrobe" or "catalog"
    wardrobe_item_id: Optional[str] = None
    product_id: Optional[str] = None
    name: str
    category: str
    sub_category: Optional[str] = None
    primary_color: Optional[str] = None
    color_tags: list[str] = []
    fit: Optional[str] = None
    price: Optional[float] = None
    price_cents: Optional[int] = None
    thumbnail_url: Optional[str] = None
    image_url: Optional[str] = None


class OutfitResponse(BaseModel):
    id: str
    user_id: str
    occasion: str
    vibe: Optional[str] = None
    skeleton: str
    score: float
    component_scores: dict[str, float] = {}
    reasons: list[str] = []
    ai_summary: Optional[str] = None
    wardrobe_only: bool = True
    fallback_reason: Optional[str] = None
    unlocked_by_product_id: Optional[str] = None
    is_saved: bool = False
    items: list[OutfitSlotItem] = []
    created_at: Optional[str] = None


class GenerateOutfitsResponse(BaseModel):
    outfits: list[OutfitResponse] = []
    status: str = "success"  # "success", "empty_wardrobe", "missing_required_slots", "no_matching_combinations"
    message: Optional[str] = None
    missing_slots: list[str] = []
    profile_warning: Optional[str] = None
    budget_status: Optional[str] = None  # "within_budget", "no_products_in_budget"
    no_products_in_budget: bool = False
    cheapest_alternative: Optional[dict[str, Any]] = None


class SavedOutfitsListResponse(BaseModel):
    outfits: list[OutfitResponse] = []
    total: int = 0
