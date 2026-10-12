"""Pydantic schemas for the private wardrobe flow."""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


VALID_CATEGORIES = {
    "top",
    "bottom",
    "dress",
    "saree",
    "ethnic_set",
    "outer",
    "layer",
    "shoes",
    "bag",
    "jewelry",
    "dupatta",
    "accessory",
}

VALID_SLOTS = {
    "top",
    "bottom",
    "ethnic_bottom",
    "dress",
    "saree",
    "ethnic_set",
    "layer",
    "shoes",
    "bag",
    "jewelry",
    "dupatta",
}


class UploadUrlRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(default="image/jpeg")


class UploadUrlResponse(BaseModel):
    upload_url: str
    token: str
    storage_path: str


class FinalizeUploadRequest(BaseModel):
    storage_path: str = Field(..., min_length=5, description="Storage path in wardrobe bucket")
    category: str = Field(..., description="High-level garment category")
    sub_category: Optional[str] = Field(default=None, description="Specific garment subtype")
    primary_color: Optional[str] = Field(default=None, description="Dominant color")
    fit: Optional[str] = Field(default=None, description="Fit: slim, regular, relaxed, oversized")
    pattern: Optional[str] = Field(default="solid", description="Fabric pattern: solid, floral, etc.")
    notes: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        clean = v.strip().lower()
        if clean not in VALID_CATEGORIES:
            raise ValueError(f"Category '{v}' is not recognized. Allowed: {sorted(VALID_CATEGORIES)}")
        return clean


class WardrobeItemUpdate(BaseModel):
    category: Optional[str] = None
    slot: Optional[str] = None
    sub_category: Optional[str] = None
    primary_color: Optional[str] = None
    color_tags: Optional[list[str]] = None
    fit: Optional[str] = None
    formality: Optional[int] = Field(default=None, ge=0, le=3)
    occasions: Optional[list[str]] = None
    seasons: Optional[list[str]] = None
    style_tags: Optional[list[str]] = None
    pattern: Optional[str] = None
    neckline: Optional[str] = None
    rise: Optional[str] = None
    length: Optional[str] = None
    notes: Optional[str] = None
    needs_review: Optional[bool] = None

    @field_validator("slot")
    @classmethod
    def validate_slot(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            clean = v.strip().lower()
            if clean not in VALID_SLOTS:
                raise ValueError(f"Slot '{v}' is not valid. Allowed: {sorted(VALID_SLOTS)}")
            return clean
        return v


class WardrobeItemResponse(BaseModel):
    id: str
    user_id: str
    image_url: str
    storage_path: str
    thumbnail_path: Optional[str] = None
    signed_image_url: Optional[str] = None
    signed_thumbnail_url: Optional[str] = None
    category: str
    slot: str
    sub_category: Optional[str] = None
    color_tags: list[str] = []
    primary_color: Optional[str] = None
    fit: Optional[str] = None
    formality: Optional[int] = 1
    occasions: list[str] = []
    seasons: list[str] = []
    style_tags: list[str] = []
    pattern: Optional[str] = "solid"
    neckline: Optional[str] = None
    rise: Optional[str] = None
    length: Optional[str] = None
    notes: Optional[str] = None
    needs_review: bool = True
    metadata: dict[str, Any] = {}
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class WardrobeListResponse(BaseModel):
    items: list[WardrobeItemResponse]
    total: int
    page: int
    page_size: int


class WardrobeCoverageResponse(BaseModel):
    total_items: int
    needs_review_count: int
    slots: dict[str, int]
    core_coverage: dict[str, int]
    is_ready_for_outfits: bool
    missing_slots: list[str]
    critical_missing: list[str]


class TagSuggestionResponse(BaseModel):
    category: str
    slot: str
    sub_category: Optional[str] = None
    primary_color: str = "black"
    color_tags: list[str] = []
    fit: Optional[str] = "regular"
    pattern: Optional[str] = "solid"
    formality: int = 1
    occasions: list[str] = []
    seasons: list[str] = []
    style_tags: list[str] = []
    source: str = "openrouter"  # "openrouter" | "deterministic_template" | "deterministic_fallback"
    requires_user_confirmation: bool = True
    message: Optional[str] = None

