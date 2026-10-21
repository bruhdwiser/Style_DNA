"""Garment taxonomy mapping, tag derivation, and slot coverage calculations.

Maps raw user inputs (category, sub_category, primary_color, fit) to engine-compatible
styling attributes (slot, formality, occasions, seasons, style_tags, color_tags).
Derived tags always start in a `needs_review = True` state so users can inspect and correct them.
"""

from __future__ import annotations

from typing import Any, Optional


# Canonical piece roles
class PieceRole:
    TOP = "top"
    BOTTOM = "bottom"
    ETHNIC_BOTTOM = "ethnic_bottom"
    DRESS = "dress"
    ETHNIC_SET = "ethnic_set"
    SAREE = "saree"
    LEHENGA_SEPARATE = "lehenga_separate"
    LAYER = "layer"
    SHOES = "shoes"
    BAG = "bag"
    JEWELRY = "jewelry"
    DUPATTA = "dupatta"
    ACCESSORY = "accessory"


# Canonical occasion taxonomy and synonyms
CANONICAL_OCCASIONS: set[str] = {
    "casual",
    "work",
    "party",
    "formal",
    "date_night",
    "gym",
    "lounge",
    "festive",
    "wedding",
    "college",
}

OCCASION_SYNONYMS: dict[str, str] = {
    "date": "date_night",
    "date_night": "date_night",
    "office": "work",
    "daily": "casual",
    "traditional": "festive",
    "festive_formal": "wedding",
    "workout": "gym",
    "active": "gym",
    "fitness": "gym",
    "night_out": "party",
    "club": "party",
    "clubbing": "party",
    "haldi": "festive",
    "mehendi": "festive",
    "sangeet": "festive",
    "puja": "festive",
    "diwali": "festive",
}


def canonical_occasion(occasion: Optional[str]) -> str:
    """Normalize occasion to canonical name preserving synonyms."""
    if not occasion:
        return "casual"
    clean = str(occasion).strip().lower().replace(" ", "_")
    return OCCASION_SYNONYMS.get(clean, clean)


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
    "lehenga_skirt": "ethnic_bottom",
    "lehenga_bottom": "ethnic_bottom",
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

# Subcategory overrides for canonical piece role
SUBCATEGORY_TO_ROLE: dict[str, str] = {
    "lehenga_skirt": PieceRole.LEHENGA_SEPARATE,
    "lehenga_bottom": PieceRole.LEHENGA_SEPARATE,
    "palazzo": PieceRole.ETHNIC_BOTTOM,
    "salwar": PieceRole.ETHNIC_BOTTOM,
    "churidar": PieceRole.ETHNIC_BOTTOM,
    "ethnic_skirt": PieceRole.ETHNIC_BOTTOM,
    "saree": PieceRole.SAREE,
    "anarkali": PieceRole.ETHNIC_SET,
    "lehenga": PieceRole.ETHNIC_SET,
    "kurta_set": PieceRole.ETHNIC_SET,
    "co-ord": PieceRole.ETHNIC_SET,
    "dupatta": PieceRole.DUPATTA,
    "blazer": PieceRole.LAYER,
    "jacket": PieceRole.LAYER,
    "cardigan": PieceRole.LAYER,
    "shrug": PieceRole.LAYER,
    "coat": PieceRole.LAYER,
}

CATEGORY_TO_ROLE: dict[str, str] = {
    "top": PieceRole.TOP,
    "bottom": PieceRole.BOTTOM,
    "ethnic_bottom": PieceRole.ETHNIC_BOTTOM,
    "dress": PieceRole.DRESS,
    "saree": PieceRole.SAREE,
    "ethnic_set": PieceRole.ETHNIC_SET,
    "outer": PieceRole.LAYER,
    "layer": PieceRole.LAYER,
    "shoes": PieceRole.SHOES,
    "bag": PieceRole.BAG,
    "jewelry": PieceRole.JEWELRY,
    "dupatta": PieceRole.DUPATTA,
    "accessory": PieceRole.ACCESSORY,
}


def derive_canonical_role(category: str, sub_category: Optional[str] = None) -> str:
    """Map legacy category and subcategory into canonical piece role."""
    sub_norm = (sub_category or "").strip().lower().replace(" ", "_")
    cat_norm = (category or "top").strip().lower().replace(" ", "_")
    return SUBCATEGORY_TO_ROLE.get(sub_norm) or CATEGORY_TO_ROLE.get(cat_norm, PieceRole.TOP)

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

    # Determine role
    role = derive_canonical_role(cat_norm, sub_norm)

    return {
        "slot": slot,
        "role": role,
        "formality": formality,
        "occasions": occasions,
        "seasons": seasons,
        "style_tags": style_tags,
        "color_tags": color_tags,
        "needs_review": True,
    }


def calculate_slot_coverage(
    items: list[dict[str, Any]],
    *,
    allow_shoeless: bool = False,
) -> dict[str, Any]:
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

    # Has enough core items to form a body look
    has_core_look = (total_one_piece >= 1 or (total_tops >= 1 and total_bottoms >= 1))
    can_generate_shoeless = has_core_look and len(items) >= 1

    if allow_shoeless:
        core_missing_no_shoes = [s for s in critical_missing if s != "shoes"]
        is_ready = len(core_missing_no_shoes) == 0 and len(items) >= (1 if total_one_piece >= 1 else 2)
    else:
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
        "can_generate_shoeless": can_generate_shoeless,
        "missing_slots": missing_slots,
        "critical_missing": critical_missing,
    }


def classify_outfit_core(candidate_or_slots: Any) -> str:
    """Classify outfit structure into explicit core category.

    Categories:
    - saree
    - one_piece (western dress)
    - lehenga_separates
    - sets (co-ord, kurta_set, anarkali)
    - ethnic_fusion (e.g. western top + ethnic skirt/palazzo, or kurti + jeans)
    - western_separates (standard top + pants/shorts/skirt)
    """
    if hasattr(candidate_or_slots, "slots"):
        slots = candidate_or_slots.slots
    elif isinstance(candidate_or_slots, dict) and "slots" in candidate_or_slots:
        slots = candidate_or_slots["slots"]
    elif isinstance(candidate_or_slots, dict):
        slots = candidate_or_slots
    else:
        slots = {}

    def _val(item: Any, key: str) -> str:
        if isinstance(item, dict):
            return str(item.get(key) or "").strip().lower()
        return str(getattr(item, key, None) or "").strip().lower()

    if "saree" in slots:
        return "saree"

    if "dress" in slots:
        return "one_piece"

    if "ethnic_set" in slots:
        set_item = slots["ethnic_set"]
        sub = _val(set_item, "sub_category") or _val(set_item, "subtype")
        if "lehenga" in sub:
            return "lehenga_separates"
        return "sets"

    top = slots.get("top")
    bottom = slots.get("bottom") or slots.get("ethnic_bottom")

    if top and bottom:
        top_cat = _val(top, "category")
        top_sub = _val(top, "sub_category") or _val(top, "subtype")
        bot_cat = _val(bottom, "category")
        bot_sub = _val(bottom, "sub_category") or _val(bottom, "subtype")

        if "lehenga" in bot_sub or "lehenga" in bot_cat:
            return "lehenga_separates"

        is_ethnic_bottom = bot_cat == "ethnic_bottom" or bot_sub in {
            "palazzo", "salwar", "churidar", "ethnic_skirt", "dhoti", "sharara"
        }
        is_ethnic_top = "kurta" in top_sub or "kurti" in top_sub or "choli" in top_sub

        if is_ethnic_top and is_ethnic_bottom:
            return "sets"
        if is_ethnic_top or is_ethnic_bottom:
            return "ethnic_fusion"

        return "western_separates"

    return "western_separates"
