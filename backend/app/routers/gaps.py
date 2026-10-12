"""Wardrobe gap analysis and catalog suggestion router.

Calculates counterfactual outfit combinations unlocked by adding a missing slot/archetype.
Ranks gaps by useful outfits unlocked and attaches real Supabase catalog products
filtered by UUID, audience (women/unisex), occasion, and budget.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query

from ..core.exceptions import AppException
from ..core.security import get_current_token, get_current_user
from ..core.supabase import get_user_scoped_supabase_client
from ..schemas.gaps import (
    CatalogProductSuggestion,
    GapAnalysisResponse,
    GapSuggestionItem,
)
from ..schemas.user import AuthenticatedUser
from ..styling.gaps import rank_gaps

logger = logging.getLogger("flashfit.gaps")

router = APIRouter(prefix="/gaps", tags=["Gaps & Catalog Suggestions"])


# ==============================================================================
# Helper Functions
# ==============================================================================


def _is_valid_uuid(val: Any) -> bool:
    """Verify that value is a well-formed UUID string."""
    try:
        uuid.UUID(str(val))
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def _matches_audience(product_audience: Optional[str]) -> bool:
    """Filter women/unisex products only in styling suggestions."""
    if not product_audience:
        return True
    aud = product_audience.strip().lower()
    return aud in ("women", "unisex", "all")


def _matches_slot(product_slot: Optional[str], product_cat: Optional[str], gap_category: str) -> bool:
    """Match catalog product slot and category against gap archetype category."""
    target = (gap_category or "").strip().lower()
    p_slot = (product_slot or "").strip().lower()
    p_cat = (product_cat or "").strip().lower()

    if target == "bottom":
        return p_slot in ("bottom", "ethnic_bottom") or "bottom" in p_cat or "trouser" in p_cat or "skirt" in p_cat
    if target == "shoes":
        return p_slot in ("shoes", "footwear") or "shoe" in p_cat or "footwear" in p_cat or "sneaker" in p_cat
    if target == "top":
        return p_slot in ("top", "kurta") or "top" in p_cat or "kurta" in p_cat or "shirt" in p_cat
    if target in ("saree", "dress", "ethnic_set"):
        return p_slot in (target, "dress", "saree", "ethnic_set") or target in p_cat or "ethnic" in p_cat
    if target in ("jewelry", "bag", "outer", "layer", "dupatta"):
        return p_slot in (target, "accessory") or target in p_cat or "accessory" in p_cat
    return p_slot == target or target in p_cat


def _matches_occasion(product_occasions: Any, target_occasion: Optional[str]) -> bool:
    """Check if target occasion matches product occasions (or if versatile)."""
    if not target_occasion:
        return True
    target = target_occasion.strip().lower().replace(" ", "_")
    if not product_occasions:
        return True
    if isinstance(product_occasions, list):
        normalized = [str(o).strip().lower().replace(" ", "_") for o in product_occasions]
        return target in normalized or "all_season" in normalized or "casual" in normalized
    return True


def _to_catalog_suggestion(raw_prod: dict[str, Any]) -> CatalogProductSuggestion:
    price_cents = int(raw_prod.get("price_cents") or 0)
    return CatalogProductSuggestion(
        id=str(raw_prod.get("id")),
        name=str(raw_prod.get("name", "Product")),
        price=round(price_cents / 100.0, 2),
        price_cents=price_cents,
        image_url=raw_prod.get("image_url"),
        category=raw_prod.get("category", "General"),
        slot=raw_prod.get("slot"),
        subtype=raw_prod.get("subtype"),
        audience=raw_prod.get("audience"),
        occasions=raw_prod.get("occasions") or [],
        color_tags=raw_prod.get("color_tags") or [],
        stock=int(raw_prod.get("stock", 10)),
    )


# ==============================================================================
# Gap Analysis & Suggestion Endpoints
# ==============================================================================


@router.get(
    "",
    response_model=GapAnalysisResponse,
    summary="Analyze wardrobe gaps and suggest catalog products",
)
@router.get(
    "/suggestions",
    response_model=GapAnalysisResponse,
    summary="Analyze wardrobe gaps and suggest catalog products (alias)",
)
async def get_wardrobe_gaps(
    occasion: Optional[str] = Query(None, description="Optional occasion filter (e.g. casual, work, wedding)"),
    budget_max: Optional[float] = Query(None, description="Maximum budget in INR (e.g. 2000.0)"),
    limit: int = Query(5, ge=1, le=20, description="Max number of gap suggestions to return"),
    token: str = Depends(get_current_token),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Compares valid wardrobe outfits with counterfactual outfits adding one missing slot.

    - Ranks gaps deterministically by useful outfits unlocked (utility & total new outfits).
    - Attaches up to 3 real Supabase catalog products per gap.
    - Products are strictly filtered by valid UUID, audience (women/unisex), occasion, and budget.
    - If all matching products exceed budget_max:
        budget_status = 'no_products_in_budget'
        budget_reason = 'no_products_in_budget'
        cheapest_alternative is attached.
    """
    client = get_user_scoped_supabase_client(token)

    # 1. Fetch user's wardrobe items (RLS-preserving)
    try:
        wardrobe_res = (
            client.from_("wardrobe_items")
            .select("*")
            .eq("user_id", user.id)
            .execute()
        )
        wardrobe_items = wardrobe_res.data or []
    except Exception as exc:
        logger.error(f"Failed to load wardrobe items for user {user.id}: {exc}")
        raise AppException(
            message="Unable to load wardrobe items for gap analysis.",
            code="WARDROBE_LOAD_ERROR",
            status_code=500,
        )

    # 2. Format wardrobe items for the styling engine
    engine_items = [
        {
            "id": str(raw["id"]),
            "category": raw.get("slot") or raw.get("category", "top"),
            "slot": raw.get("slot", "top"),
            "sub_category": raw.get("sub_category"),
            "color": raw.get("primary_color"),
            "colors": raw.get("color_tags") or [],
            "fit": raw.get("fit"),
            "formality": raw.get("formality", 1),
            "occasions": raw.get("occasions") or [],
            "seasons": raw.get("seasons") or [],
            "styles": raw.get("style_tags") or [],
            "pattern": raw.get("pattern", "solid"),
            "is_available": True,
        }
        for raw in wardrobe_items
    ]

    # 3. Calculate counterfactual gap rankings
    occasions_filter = [occasion.strip().lower()] if occasion else None
    ranked_gaps = rank_gaps(engine_items, occasions=occasions_filter)

    # 4. Fetch catalog products from Supabase
    try:
        products_res = client.from_("products").select("*").execute()
        all_catalog_products = products_res.data or []
    except Exception as exc:
        logger.warning(f"Could not load catalog products for gap suggestions: {exc}")
        all_catalog_products = []

    # Filter catalog products by valid UUID and women/unisex audience
    eligible_products = [
        p
        for p in all_catalog_products
        if _is_valid_uuid(p.get("id")) and _matches_audience(p.get("audience"))
    ]

    budget_cents = int(budget_max * 100) if budget_max is not None and budget_max > 0 else None

    # 5. Attach matching catalog products and evaluate budget status for each gap
    gap_suggestion_items: list[GapSuggestionItem] = []

    for gap in ranked_gaps:
        gap_cat = gap.get("category", "top")

        # Candidate products matching slot and occasion
        candidates = [
            p
            for p in eligible_products
            if _matches_slot(p.get("slot"), p.get("category"), gap_cat)
            and _matches_occasion(p.get("occasions"), occasion)
        ]

        # Sort candidates deterministically by price ascending
        candidates.sort(key=lambda p: int(p.get("price_cents") or 0))

        matching_suggestions: list[CatalogProductSuggestion] = []
        budget_status = "within_budget"
        budget_reason: Optional[str] = None
        cheapest_alt: Optional[CatalogProductSuggestion] = None

        if budget_cents is not None:
            in_budget = [p for p in candidates if int(p.get("price_cents") or 0) <= budget_cents]
            if in_budget:
                matching_suggestions = [_to_catalog_suggestion(p) for p in in_budget[:3]]
                budget_status = "within_budget"
                budget_reason = None
            elif candidates:
                # All candidates for this slot exceed user budget
                matching_suggestions = []
                budget_status = "no_products_in_budget"
                budget_reason = "no_products_in_budget"
                cheapest_alt = _to_catalog_suggestion(candidates[0])
            else:
                matching_suggestions = []
                budget_status = "no_products_found"
                budget_reason = f"No catalog products found for slot '{gap_cat}'"
        else:
            if candidates:
                matching_suggestions = [_to_catalog_suggestion(p) for p in candidates[:3]]
                budget_status = "within_budget"
                budget_reason = None
            else:
                matching_suggestions = []
                budget_status = "no_products_found"
                budget_reason = f"No catalog products found for slot '{gap_cat}'"

        gap_suggestion_items.append(
            GapSuggestionItem(
                id=gap["id"],
                name=gap["name"],
                category=gap["category"],
                slot=gap["category"],
                suitability=gap["suitability"],
                new_outfits_total=gap["new_outfits_total"],
                new_outfits_by_occasion=gap.get("new_outfits_by_occasion", {}),
                utility=gap["utility"],
                matching_products=matching_suggestions,
                budget_status=budget_status,
                budget_reason=budget_reason,
                cheapest_alternative=cheapest_alt,
            )
        )

    # Slice to limit
    limited_gaps = gap_suggestion_items[:limit]

    message = None
    if not wardrobe_items:
        message = "Your wardrobe is empty. These core essentials will unlock the largest number of versatile outfits."
    elif all(g.utility == 0 for g in limited_gaps):
        message = "Your wardrobe has strong coverage! These pieces add subtle styling variety."

    return GapAnalysisResponse(
        gaps=limited_gaps,
        total_gaps=len(gap_suggestion_items),
        wardrobe_item_count=len(wardrobe_items),
        occasion_filter=occasion,
        budget_max=budget_max,
        message=message,
    )
