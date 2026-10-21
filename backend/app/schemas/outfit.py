"""Pydantic schemas for outfit generation and saved looks."""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


from ..core.exceptions import AppException

APPROVED_OUTFIT_TAGS = ["Work", "Date Night", "Wedding", "Vacation", "Try Later"]
APPROVED_OUTFIT_TAGS_MAP = {t.lower(): t for t in APPROVED_OUTFIT_TAGS}


def validate_and_normalize_tags(
    raw_tags: Optional[list[str]],
    *,
    allow_default: bool = False,
    default_tags: Optional[list[str]] = None,
) -> list[str]:
    """Validate and normalize outfit tags to approved canonical labels.

    - Normalizes case and collapses irregular whitespace (e.g. '  date   night  ' -> 'Date Night').
    - Deduplicates identical canonical tags preserving order.
    - If allow_default is True and raw_tags is None (or empty), returns default_tags or ['Try Later'].
    - If allow_default is False and raw_tags is empty, returns [].
    - Rejects any tag not present in APPROVED_OUTFIT_TAGS with an AppException(422).
    """
    if raw_tags is None:
        if allow_default:
            return list(default_tags or ["Try Later"])
        return []

    if len(raw_tags) == 0:
        if allow_default:
            return list(default_tags or ["Try Later"])
        return []

    normalized: list[str] = []
    for t in raw_tags:
        if not isinstance(t, str):
            raise AppException(
                message=f"Tag must be a string, got {type(t).__name__}.",
                code="INVALID_TAG",
                status_code=422,
            )
        clean = " ".join(t.strip().split())
        if not clean:
            raise AppException(
                message=f"Empty tag is not permitted. Approved tags are: {', '.join(APPROVED_OUTFIT_TAGS)}.",
                code="INVALID_TAG",
                status_code=422,
            )
        canonical = APPROVED_OUTFIT_TAGS_MAP.get(clean.lower())
        if not canonical:
            raise AppException(
                message=f"Unsupported tag '{t}'. Approved tags are: {', '.join(APPROVED_OUTFIT_TAGS)}.",
                code="INVALID_TAG",
                status_code=422,
            )
        if canonical not in normalized:
            normalized.append(canonical)

    return normalized


def normalize_outfit_tags(raw_tags: Optional[list[str]]) -> list[str]:
    """Backward-compatible helper defaulting to ['Try Later'] for save flows."""
    return validate_and_normalize_tags(raw_tags, allow_default=True)


class GenerateOutfitsRequest(BaseModel):
    occasion: str = Field(default="casual", description="Occasion: casual, work, party, formal, festive, wedding, lounge, college")
    vibe: Optional[str] = Field(default=None, description="Aesthetic vibe: minimal, classic, bohemian, streetwear, elegant")
    vibes: Optional[list[str]] = Field(default=None, description="Multiple aesthetic vibes for multi-label ranking")
    season: str = Field(default="all_season", description="Seasonal filter: summer, winter, monsoon, all_season")
    wardrobe_only: bool = Field(default=False, description="Strictly wardrobe items only (opt out of catalog completion)")
    allow_one_new_item: Optional[bool] = Field(default=None, description="Legacy alias: if True, enables catalog completion")
    budget_max: Optional[float] = Field(default=None, description="Maximum price in INR for catalog item")
    min_quality_threshold: float = Field(default=0.70, description="Minimum score threshold below which fallback can be activated")
    limit: int = Field(default=6, ge=1, le=20, description="Maximum number of diversified outfits to generate")
    seed: Optional[int] = Field(default=None, description="Random seed for varied, non-redundant outfit recommendations")
    is_shuffle: bool = Field(default=False, description="Shuffle mode for fresh alternative recommendations")
    exclude_core_signatures: Optional[list[list[tuple[str, str]]]] = Field(default=None, description="Core signatures to exclude on shuffle")


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
    vibes: Optional[list[str]] = None
    season: Optional[str] = None
    shoes_included: bool = True
    formality_spread: Optional[int] = None
    core_type: Optional[str] = None
    skeleton: str
    score: float
    component_scores: dict[str, float] = {}
    reasons: list[str] = []
    ai_summary: Optional[str] = None
    wardrobe_only: bool = True
    fallback_reason: Optional[str] = None
    unlocked_by_product_id: Optional[str] = None
    is_saved: bool = False
    is_below_threshold: bool = False
    quality_warning: Optional[str] = None
    vibe_coverage: Optional[str] = Field(default=None, description="Wardrobe coverage for requested vibe: high, moderate, low, none")
    tags: list[str] = Field(default_factory=list, description="Classification tags for saved looks")
    core_signature: list[tuple[str, str]] = Field(default_factory=list, description="Sorted (slot, item_id) pairs of core garments")
    items: list[OutfitSlotItem] = []
    created_at: Optional[str] = None


class SaveOutfitRequest(BaseModel):
    tags: Optional[list[str]] = Field(default=None, description="Optional classification tags (e.g. Work, Date Night, Wedding, Vacation, Try Later)")


class SaveOutfitResponse(BaseModel):
    success: bool = True
    message: str
    is_saved: bool = True
    tags: list[str] = Field(default_factory=list)


class UpdateOutfitTagsRequest(BaseModel):
    tags: list[str] = Field(..., description="Tags to assign to the saved outfit")


class GenerateOutfitsResponse(BaseModel):
    outfits: list[OutfitResponse] = []
    status: str = "success"  # "success", "partial_results", "empty_wardrobe", "missing_required_slots", "no_matching_combinations"
    message: Optional[str] = None
    missing_slots: list[str] = []
    profile_warning: Optional[str] = None
    quality_warning: Optional[str] = None
    vibe_coverage: Optional[str] = Field(default=None, description="Wardrobe coverage evaluation for requested vibe")
    budget_status: Optional[str] = None  # "within_budget", "no_products_in_budget", "no_products_found"
    no_products_in_budget: bool = False
    cheapest_alternative: Optional[dict[str, Any]] = None


class SavedOutfitsListResponse(BaseModel):
    outfits: list[OutfitResponse] = []
    total: int = 0
    available_tags: list[str] = Field(default_factory=list, description="Unique set of tags present across user's saved looks")
