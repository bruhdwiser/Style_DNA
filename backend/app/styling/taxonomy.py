"""Garment taxonomy mapping, tag derivation, and slot coverage calculations.

Maps raw user inputs (category, sub_category, primary_color, fit) to engine-compatible
styling attributes (slot, formality, occasions, seasons, style_tags, color_tags).
Derived tags always start in a `needs_review = True` state so users can inspect and correct them.
"""

from __future__ import annotations

from typing import Any, Optional


# Canonical category to default slot mapping
CATEGORY_TO_SLOT: dict[str, str] = {
    "top": "top",
    "bottom": "bottom",
    "dress": "dress",
    "saree": "saree",
    "ethnic_set": "ethnic_set",
    "outer": "layer",
    "layer": "layer",
    "shoes": "shoes",
    "bag": "bag",
    "jewelry": "jewelry",
    "dupatta": "dupatta",
    "accessory": "jewelry",
}

# Subcategory overrides for slot
SUBCATEGORY_TO_SLOT: dict[str, str] = {
    "palazzo": "ethnic_bottom",
    "salwar": "ethnic_bottom",
    "churidar": "ethnic_bottom",
    "ethnic_skirt": "ethnic_bottom",
    "saree": "saree",
    "anarkali": "ethnic_set",
    "lehenga": "ethnic_set",
    "kurta_set": "ethnic_set",
    "co-ord": "ethnic_set",
    "dupatta": "dupatta",
    "blazer": "layer",
    "jacket": "layer",
    "cardigan": "layer",
    "shrug": "layer",
    "coat": "layer",
}

# Formality by subcategory (0=casual, 1=smart casual, 2=formal, 3=festive/wedding)
SUBCATEGORY_FORMALITY: dict[str, int] = {
    "t-shirt": 0,
    "crop_top": 0,
    "tank": 0,
    "hoodie": 0,
    "sweatshirt": 0,
    "jeans": 0,
    "shorts": 0,
    "sneakers": 0,
    "flats": 0,
    "flip_flops": 0,
    "shirt": 1,
    "blouse": 1,
    "polo": 1,
    "chinos": 1,
    "trousers": 1,
    "midi_dress": 1,
    "loafers": 1,
    "sandals": 1,
    "tote": 1,
    "blazer": 2,
    "suit": 2,
    "pencil_skirt": 2,
    "formal_trousers": 2,
    "heels": 2,
    "oxford": 2,
    "coat": 2,
    "handbag": 2,
    "saree": 3,
    "lehenga": 3,
    "anarkali": 3,
    "juttis": 3,
    "clutch": 3,
    "jewelry": 3,
    "dupatta": 3,
}

FORMALITY_OCCASIONS: dict[int, list[str]] = {
    0: ["casual", "college", "lounge"],
    1: ["casual", "work", "college", "party", "date"],
    2: ["work", "formal", "party", "date"],
    3: ["festive", "wedding", "formal", "party", "date"],
}

SUBCATEGORY_STYLES: dict[str, list[str]] = {
    "t-shirt": ["casual", "streetwear"],
    "hoodie": ["streetwear", "casual"],
    "shirt": ["classic", "minimal"],
    "blouse": ["elegant", "classic"],
    "blazer": ["classic", "minimal"],
    "saree": ["traditional", "elegant"],
    "kurta": ["traditional", "casual"],
    "anarkali": ["traditional", "festive"],
    "lehenga": ["traditional", "festive"],
    "maxi_dress": ["bohemian", "elegant"],
    "midi_dress": ["classic", "minimal"],
    "jeans": ["casual", "streetwear"],
    "sneakers": ["streetwear", "casual"],
    "heels": ["elegant", "classic"],
    "juttis": ["traditional"],
}

SUMMER_SUBCATEGORIES = {"shorts", "tank", "crop_top", "sandals", "mini_dress"}
WINTER_SUBCATEGORIES = {"coat", "jacket", "hoodie", "sweatshirt", "sweater", "boots"}


def derive_taxonomy_tags(
    category: str,
    sub_category: Optional[str] = None,
    primary_color: Optional[str] = None,
    fit: Optional[str] = None,
) -> dict[str, Any]:
    """Deterministically derive styling attributes from quick-tag inputs."""
    cat_norm = (category or "top").strip().lower().replace(" ", "_")
    sub_norm = (sub_category or "").strip().lower().replace(" ", "_")
    color_norm = (primary_color or "").strip().lower()

    # Determine slot
    slot = SUBCATEGORY_TO_SLOT.get(sub_norm) or CATEGORY_TO_SLOT.get(cat_norm, "top")

    # Determine formality
    if sub_norm in SUBCATEGORY_FORMALITY:
        formality = SUBCATEGORY_FORMALITY[sub_norm]
    elif cat_norm in ("saree", "ethnic_set"):
        formality = 3
    elif cat_norm == "layer":
        formality = 2
    elif cat_norm in ("shoes", "bag", "jewelry"):
        formality = 1
    else:
        formality = 1

    # Determine occasions
    occasions = list(FORMALITY_OCCASIONS.get(formality, ["casual"]))
    if sub_norm in ("kurta", "saree", "anarkali", "lehenga"):
        if "festive" not in occasions:
            occasions.append("festive")

    # Determine seasons
    if sub_norm in SUMMER_SUBCATEGORIES:
        seasons = ["summer", "all_season"]
    elif sub_norm in WINTER_SUBCATEGORIES:
        seasons = ["winter", "all_season"]
    else:
        seasons = ["all_season"]

    # Determine style tags
    style_tags = list(SUBCATEGORY_STYLES.get(sub_norm, ["classic", "casual"]))

    # Color tags
    color_tags = [color_norm] if color_norm else []

    return {
        "slot": slot,
        "formality": formality,
        "occasions": occasions,
        "seasons": seasons,
        "style_tags": style_tags,
        "color_tags": color_tags,
        "needs_review": True,
    }


def calculate_slot_coverage(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate slot distribution, core coverage, and outfit readiness."""
    slot_counts: dict[str, int] = {
        "top": 0,
        "bottom": 0,
        "ethnic_bottom": 0,
        "dress": 0,
        "saree": 0,
        "ethnic_set": 0,
        "shoes": 0,
        "layer": 0,
        "bag": 0,
        "jewelry": 0,
        "dupatta": 0,
    }

    needs_review_count = 0

    for item in items:
        slot = item.get("slot") or "top"
        slot_counts[slot] = slot_counts.get(slot, 0) + 1
        if item.get("needs_review"):
            needs_review_count += 1

    # Core outfit groupings
    total_tops = slot_counts.get("top", 0)
    total_bottoms = slot_counts.get("bottom", 0) + slot_counts.get("ethnic_bottom", 0)
    total_one_piece = (
        slot_counts.get("dress", 0)
        + slot_counts.get("saree", 0)
        + slot_counts.get("ethnic_set", 0)
    )
    total_shoes = slot_counts.get("shoes", 0)

    critical_missing: list[str] = []
    if total_shoes == 0:
        critical_missing.append("shoes")
    if total_tops == 0 and total_one_piece == 0:
        critical_missing.append("tops_or_one_piece")
    elif total_tops > 0 and total_bottoms == 0 and total_one_piece == 0:
        critical_missing.append("bottoms")

    is_ready = len(critical_missing) == 0 and len(items) >= 2

    missing_slots = [s for s, count in slot_counts.items() if count == 0]

    return {
        "total_items": len(items),
        "needs_review_count": needs_review_count,
        "slots": slot_counts,
        "core_coverage": {
            "tops": total_tops,
            "bottoms": total_bottoms,
            "one_piece": total_one_piece,
            "shoes": total_shoes,
            "layers": slot_counts.get("layer", 0),
            "accessories": slot_counts.get("bag", 0) + slot_counts.get("jewelry", 0) + slot_counts.get("dupatta", 0),
        },
        "is_ready_for_outfits": is_ready,
        "missing_slots": missing_slots,
        "critical_missing": critical_missing,
    }
