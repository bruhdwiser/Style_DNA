"""Pydantic schemas for counterfactual gap analysis and product suggestions."""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


class CatalogProductSuggestion(BaseModel):
    id: str
    name: str
    price: float
    price_cents: int
    image_url: Optional[str] = None
    category: str
    slot: Optional[str] = None
    subtype: Optional[str] = None
    audience: Optional[str] = None
    occasions: list[str] = []
    color_tags: list[str] = []
    stock: int = 10


class GapSuggestionItem(BaseModel):
    id: str
    name: str
    category: str
    slot: str
    suitability: float
    new_outfits_total: int
    new_outfits_by_occasion: dict[str, int] = {}
    utility: float
    matching_products: list[CatalogProductSuggestion] = []
    budget_status: str = "within_budget"  # "within_budget", "no_products_in_budget", "no_products_found"
    budget_reason: Optional[str] = None
    cheapest_alternative: Optional[CatalogProductSuggestion] = None


class GapAnalysisResponse(BaseModel):
    gaps: list[GapSuggestionItem] = []
    total_gaps: int = 0
    wardrobe_item_count: int = 0
    occasion_filter: Optional[str] = None
    budget_max: Optional[float] = None
    message: Optional[str] = None
