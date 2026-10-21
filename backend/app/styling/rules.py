"""Hard filters and deterministic outfit rule helpers.

Ported from StyleSenseAI outfits/rules.py — pure Python, no I/O.

Occasion-specific constraints:
- Formal/wedding occasions require formality ≥ 3.
- Lounge/casual occasions reject formal shoes.
- Season filtering supports aliases (e.g. spring → spring_autumn, all_season).
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.styling.taxonomy import canonical_occasion


OUTFIT_RULE_CONFIG: dict[str, Any] = {
    "formality_bands": {
        "casual": 1,
        "college": 1,
        "lounge": 1,
        "work": 2,
        "date": 2,
        "date_night": 3,
        "party": 3,
        "festive": 3,
        "formal": 4,
        "wedding": 4,
    },
    "season_aliases": {
        "summer": {"summer", "all_season"},
        "winter": {"winter", "all_season"},
        "spring": {"spring_autumn", "all_season"},
        "monsoon": {"monsoon", "all_season"},
    },
    "weights": {
        "occasion_fit": 0.18,
        "pairing_strength": 0.16,
        "color_harmony": 0.16,
        "style_coherence": 0.14,
        "vibe_affinity": 0.10,
        "formality_fit": 0.08,
        "season_fit": 0.06,
        "freshness": 0.06,
        "style_dna": 0.04,
        "layering": 0.02,
        # Legacy aliases
        "body_fit": 0.00,
        "color": 0.00,
        "style": 0.00,
        "occasion": 0.00,
        "season": 0.00,
        "novelty": 0.00,
    },
}

# Threshold configuration constants
MIN_OUTFIT_SCORE_RECOMMENDATION: float = 0.55
MIN_OUTFIT_SCORE_GAP_ANALYSIS: float = 0.65
MIN_OUTFIT_SCORE_CATALOG_COMPLETION: float = 0.60
HIGH_CONFIDENCE_THRESHOLD: float = 0.70

LOUD_PATTERNS: frozenset[str] = frozenset({
    "loud",
    "bold",
    "animal_print",
    "leopard",
    "zebra",
    "floral_bold",
    "floral",
    "plaid_wide",
    "abstract_bold",
    "camo",
    "chevron",
    "tie_dye",
    "paisley_bold",
    "paisley",
    "block_print",
    "graphic",
    "bandhani",
    "colour_block",
})


def is_item_available(item: Any) -> bool:
    """Return False if item is marked unavailable in boolean or string format."""
    val = _coerce_item(item, "is_available", None)
    if val is None:
        val = _coerce_item(item, "available", True)
    if isinstance(val, str):
        return val.strip().lower() not in ("false", "0", "no", "n")
    return bool(val)


def _normalize(value: Any) -> str:
    return str(value).strip().lower().replace(" ", "_")


def _coerce_item(item: Any, key: str, default: Any = None) -> Any:
    """Attribute accessor that handles both dicts and objects with underscore variants."""
    if isinstance(item, dict):
        return item.get(key, item.get(key.replace("_", ""), default))
    return getattr(item, key, default)


def _iter_slots(candidate: Any) -> Iterable[tuple[str, Any]]:
    """Iterate (slot_name, item) pairs from a candidate (dict or dataclass)."""
    if isinstance(candidate, dict):
        slots = candidate.get("slots", candidate)
        if isinstance(slots, dict):
            return slots.items()
        return ()
    slots = getattr(candidate, "slots", {})
    if isinstance(slots, dict):
        return slots.items()
    return ()


def occasion_to_formality_band(occasion: Any) -> int:
    """Map an occasion string or list to a formality band 1..4."""
    if isinstance(occasion, (list, tuple, set)):
        return (
            max(occasion_to_formality_band(item) for item in occasion)
            if occasion
            else 1
        )
    key = _normalize(occasion)
    return OUTFIT_RULE_CONFIG["formality_bands"].get(key, 1)


def season_match(item: Any, season: Any) -> bool:
    """Check whether an item is valid for a target season."""
    season_key = _normalize(season)
    if season_key in ("all_season", "all", "any"):
        return True
    values = _coerce_item(item, "season", None)
    if values is None:
        values = _coerce_item(item, "seasons", None)
    if values is None:
        return True  # Items without season data are all-season
    if isinstance(values, str):
        options = {_normalize(values)}
    elif isinstance(values, (list, tuple, set)):
        options = {_normalize(v) for v in values}
    else:
        options = {_normalize(values)}
    return any(
        option in OUTFIT_RULE_CONFIG["season_aliases"].get(season_key, {season_key, "all_season"})
        or option == "all_season"
        for option in options
    )


def duplicate_items(candidate: Any) -> bool:
    """Return True when the same item ID appears more than once."""
    seen: set[str] = set()
    for _, item in _iter_slots(candidate):
        item_id = _coerce_item(item, "id")
        if item_id is None:
            continue
        if str(item_id) in seen:
            return True
        seen.add(str(item_id))
    return False


def no_two_bottoms(candidate: Any) -> bool:
    """Reject skeletons that include more than one bottom-style category."""
    bottom_count = 0
    for slot_name, item in _iter_slots(candidate):
        category = _coerce_item(item, "category")
        if category in {"bottom", "ethnic_bottom"} or slot_name in {
            "bottom",
            "ethnic_bottom",
        }:
            bottom_count += 1
    return bottom_count <= 1


def no_formal_shoes_for_lounge(candidate: Any, occasion: Any) -> bool:
    """Reject formal shoes (heels, oxford, formal shoes) when the intended outfit is lounge-oriented."""
    occ = canonical_occasion(occasion) if occasion else ""
    if occ != "lounge":
        return True
    for _, item in _iter_slots(candidate):
        category = _coerce_item(item, "category")
        if category == "shoes":
            formality = _coerce_item(item, "formality", 1) or 1
            try:
                formality_value = int(formality)
            except (TypeError, ValueError):
                formality_value = 1
            if formality_value > 2:
                return False
    return True


def get_item_valid_occasions(item: Any) -> set[str]:
    """Derive valid canonical occasions (core + conditional stretch) from actual item attributes.

    If a required attribute for a conditional stretch is absent/missing, the stretch
    must NOT be granted.
    """
    piece_id = _normalize(_coerce_item(item, "piece_id", "") or _coerce_item(item, "sub_category", "") or _coerce_item(item, "category", ""))
    cat = _normalize(_coerce_item(item, "category", ""))
    sub = _normalize(_coerce_item(item, "sub_category", "") or _coerce_item(item, "subtype", "") or piece_id)
    fabric = _normalize(_coerce_item(item, "fabric", ""))
    pattern = _normalize(_coerce_item(item, "pattern", "solid"))
    formality = int(_coerce_item(item, "formality", 2) or 2)
    length = _normalize(_coerce_item(item, "length", ""))
    embellishment = _normalize(_coerce_item(item, "embellishment", "none"))
    wash = _normalize(_coerce_item(item, "wash", "") or _coerce_item(item, "extra_wash", ""))
    style = _normalize(_coerce_item(item, "style", ""))

    vibes_raw = _coerce_item(item, "vibes", []) or _coerce_item(item, "style_tags", []) or _coerce_item(item, "styles", [])
    if isinstance(vibes_raw, str):
        vibes = {v.strip().lower() for v in vibes_raw.replace("|", ",").split(",") if v.strip()}
    elif isinstance(vibes_raw, (list, tuple, set)):
        vibes = {str(v).strip().lower() for v in vibes_raw if v}
    else:
        vibes = set()

    # If the item already has an explicit list of occasions from DB:
    explicit_occs = _coerce_item(item, "occasions", None)
    if explicit_occs:
        if isinstance(explicit_occs, str):
            explicit_set = {_normalize(explicit_occs)}
        elif isinstance(explicit_occs, (list, tuple, set)):
            explicit_set = {_normalize(o) for o in explicit_occs if o}
        else:
            explicit_set = set()
        if explicit_set and "all" not in explicit_set and "all_season" not in explicit_set:
            if style in ("formal", "elegant") or formality >= 3:
                explicit_set.update(["formal", "wedding"])
            elif style in ("festive", "traditional"):
                explicit_set.update(["festive", "wedding"])
            return explicit_set

    valid: set[str] = set()

    # Core occasions and conditional stretch by piece type
    if piece_id in ("tshirt", "t-shirt"):
        valid.update(["casual", "college", "lounge"])
        # Work stretch: ONLY IF pattern == solid and formality >= 2 (not loud/graphic)
        if pattern == "solid" and formality >= 2 and pattern not in LOUD_PATTERNS:
            valid.add("work")

    elif piece_id == "tank":
        valid.update(["casual", "lounge", "college"])
        # Date_night / party stretch: ONLY IF fabric in ("satin", "silk")
        if fabric in ("satin", "silk"):
            valid.update(["date_night", "party"])

    elif piece_id == "crop_top":
        valid.update(["casual", "college", "party", "date_night"])

    elif piece_id in ("shirt_formal", "button_down", "formal_shirt"):
        valid.update(["work", "college", "formal"])
        # Date_night stretch: ONLY IF fabric in ("satin", "silk")
        if fabric in ("satin", "silk"):
            valid.add("date_night")

    elif piece_id in ("sweater", "knitwear"):
        valid.update(["casual", "work", "college"])

    elif piece_id in ("hoodie", "sweatshirt"):
        valid.update(["casual", "college", "lounge"])

    elif piece_id in ("kurti", "kurta", "tunic"):
        valid.update(["casual", "work", "college", "festive"])

    elif piece_id in ("blouse", "saree_blouse"):
        valid.update(["festive", "wedding", "party", "date_night"])

    elif piece_id in ("jeans", "denim"):
        valid.update(["casual", "college"])
        # Work stretch: ONLY IF wash == "dark" (present attribute required)
        if wash == "dark":
            valid.add("work")

    elif piece_id in ("trousers_casual", "cargo", "joggers"):
        valid.update(["casual", "college", "lounge"])

    elif piece_id == "skirt":
        valid.update(["casual", "college", "party", "date_night"])
        # Work stretch: ONLY IF length in ("midi", "maxi") and pattern is NOT loud
        is_loud_pat = pattern in LOUD_PATTERNS
        if length in ("midi", "maxi") and not is_loud_pat:
            valid.add("work")

    elif piece_id == "shorts":
        valid.update(["casual", "lounge"])
        # Party stretch: ONLY IF fabric in ("leather", "satin", "tailored_linen") and pattern == "solid"
        if fabric in ("leather", "satin", "tailored_linen") and pattern == "solid":
            valid.add("party")

    elif piece_id == "palazzo":
        valid.update(["casual", "college", "festive"])
        if pattern == "solid":
            valid.add("work")
        # Party stretch: if embellished or light/silk/rayon fabric
        if embellishment in ("light", "heavy") or fabric in ("silk", "rayon", "crepe"):
            valid.add("party")

    elif piece_id in ("salwar", "dhoti", "churidar"):
        valid.update(["casual", "festive", "work"])

    elif piece_id in ("lehenga_skirt", "lehenga_bottom"):
        valid.update(["festive", "wedding"])
        if formality <= 2:
            valid.update(["casual", "college"])

    elif piece_id == "midi_dress":
        valid.update(["casual", "date_night", "party"])
        # College stretch: shirt_dress
        if sub in ("shirt_dress", "tshirt_dress") or "shirt" in sub:
            valid.update(["college", "work"])

    elif piece_id == "mini_dress":
        valid.update(["party", "date_night", "casual"])

    elif piece_id == "maxi_dress":
        valid.update(["casual", "college"])
        # Date stretch: bohemian vibe
        if "bohemian" in vibes or fabric in ("silk", "chiffon", "satin"):
            valid.add("date_night")

    elif piece_id == "jumpsuit":
        valid.update(["work", "date_night", "party", "casual"])

    elif piece_id in ("coord_set", "co-ord"):
        valid.update(["casual", "college"])
        if formality >= 3:
            valid.add("work")

    elif piece_id in ("kurti_set", "kurta_set"):
        valid.update(["casual", "festive", "work"])
        # Wedding stretch: heavy embellishment and formality >= 4
        if embellishment == "heavy" and formality >= 4:
            valid.add("wedding")

    elif piece_id in ("anarkali", "lehenga_set"):
        valid.update(["festive", "wedding"])

    elif piece_id == "saree":
        valid.update(["festive", "wedding", "formal"])
        if fabric in ("cotton", "linen") and formality <= 3:
            valid.add("work")

    elif piece_id in ("jacket", "cardigan", "shrug", "ethnic_jacket", "blazer"):
        if piece_id == "blazer":
            valid.update(["work", "formal", "party", "date_night"])
        elif piece_id == "ethnic_jacket":
            valid.update(["festive", "wedding"])
        elif piece_id == "cardigan":
            valid.update(["casual", "college", "work", "lounge"])
        elif piece_id == "shrug":
            valid.update(["casual", "party"])
        else:
            valid.update(["casual", "college"])

    elif piece_id in ("sneakers", "running_shoes"):
        valid.update(["casual", "college", "lounge", "workout", "gym"])
        # Date / party stretch if streetwear vibe
        if "streetwear" in vibes:
            valid.update(["party", "date_night"])

    elif piece_id in ("chappals", "sandals", "flats"):
        valid.update(["casual", "college", "festive"])
        # Date_night / wedding stretch: metallic or embellished and formality >= 3
        if "metallic" in style or style == "metallic" or embellishment in ("light", "heavy"):
            if formality >= 3:
                valid.update(["date_night", "wedding"])

    elif piece_id in ("mules", "loafers"):
        valid.update(["casual", "work", "date_night", "college"])

    elif piece_id in ("heels", "pumps"):
        valid.update(["party", "date_night", "wedding", "formal", "work"])

    elif piece_id == "jutti":
        valid.update(["festive", "wedding", "casual", "college"])

    else:
        # Fallback by category and formality
        if cat in ("top", "bottom"):
            valid.update(["casual", "college"])
            if formality >= 3:
                valid.update(["work", "formal"])
        elif cat == "dress":
            valid.update(["casual", "party", "date_night"])
        elif cat == "shoes":
            valid.update(["casual", "college"])
        elif cat == "saree":
            valid.update(["festive", "wedding", "formal"])
        elif cat == "ethnic_set":
            valid.update(["festive", "wedding"])

    return valid


def item_occasion_match(item: Any, occasion: Any) -> bool:
    """Check whether an item is valid for a target occasion.

    Applies hard occasion exclusions (e.g. streetwear at weddings) and
    derives core vs conditional stretch eligibility from actual attributes.
    """
    if not occasion:
        return True
    target = canonical_occasion(occasion)
    if target in ("all", "any", "all_occasion"):
        return True

    piece_id = _normalize(_coerce_item(item, "piece_id", "") or _coerce_item(item, "sub_category", "") or _coerce_item(item, "category", ""))
    sub = _normalize(_coerce_item(item, "sub_category", "") or _coerce_item(item, "subtype", "") or piece_id)
    cat = _normalize(_coerce_item(item, "category", ""))
    formality = int(_coerce_item(item, "formality", 1) or 1)
    style_val = _coerce_item(item, "style", "")
    if not style_val and isinstance(_coerce_item(item, "style_tags"), (list, tuple)) and _coerce_item(item, "style_tags"):
        style_val = _coerce_item(item, "style_tags")[0]
    style = _normalize(style_val)

    # 1. Hard exclusions for wedding
    if target == "wedding":
        if piece_id in ("tshirt", "t-shirt", "hoodie", "sweatshirt", "shorts", "trousers_casual", "cargo", "joggers", "sneakers") or "sneaker" in sub or "hoodie" in sub:
            return False
        if formality < 2 or (formality < 3 and style in ("casual", "streetwear", "sporty", "lounge")):
            return False
        if cat in ("top", "bottom", "dress", "ethnic_set") and formality < 3:
            return False

    # 2. Hard exclusions for formal
    if target == "formal":
        if piece_id in ("hoodie", "sweatshirt", "shorts", "trousers_casual", "cargo", "joggers") or "hoodie" in sub:
            return False

    # 3. Derive valid occasions
    valid_occs = get_item_valid_occasions(item)
    if target in valid_occs:
        return True

    # 4. Check occasion clusters
    clusters = {
        "casual": {"casual", "college", "lounge", "daily"},
        "college": {"college", "casual"},
        "lounge": {"lounge", "casual"},
        "work": {"work", "formal", "office"},
        "formal": {"formal", "work"},
        "festive": {"festive", "wedding", "traditional"},
        "wedding": {"wedding"},
        "party": {"party", "date", "date_night"},
        "date_night": {"date_night", "date", "party"},
        "date": {"date", "date_night", "party"},
        "gym": {"gym", "workout", "active"},
    }
    allowed_cluster = clusters.get(target, {target})
    if bool(valid_occs & allowed_cluster):
        if target == "wedding" and formality < 3:
            return False
        return True

    return False


def no_sneakers_with_ethnic_formal(candidate: Any, occasion: Any) -> bool:
    """Reject casual sneakers with traditional ethnic formal looks (anarkali/saree/ethnic_set)."""
    target = canonical_occasion(occasion)
    if target in {"wedding", "festive", "formal"}:
        has_formal_ethnic = False
        has_sneakers = False
        for _, item in _iter_slots(candidate):
            cat = _normalize(_coerce_item(item, "category", ""))
            subcat = _normalize(_coerce_item(item, "sub_category", "") or _coerce_item(item, "subtype", "") or _coerce_item(item, "piece_id", ""))
            if cat in {"saree", "ethnic_set"} or subcat in {"anarkali", "saree", "anarkali_set", "sharara_set", "lehenga_set"}:
                has_formal_ethnic = True
            if cat == "shoes" and ("sneaker" in subcat or "sneakers" in subcat or subcat == "sneakers"):
                has_sneakers = True
        if has_formal_ethnic and has_sneakers:
            return False

    if target in {"casual", "college", "lounge"}:
        for _, item in _iter_slots(candidate):
            subcat = _normalize(_coerce_item(item, "sub_category", "") or _coerce_item(item, "subtype", "") or _coerce_item(item, "piece_id", ""))
            if subcat in {"anarkali", "anarkali_set", "sharara_set", "silk_saree", "kanjivaram_saree"}:
                return False

    return True



def check_formality_spread(candidate: Any) -> bool:
    """Ensure candidate outfit does not exceed max allowed formality spread.

    Rule: spread = max(formality) - min(formality) <= 2.
    If spread >= 3, return False (hard fail / candidate excluded).
    """
    formalities: list[int] = []
    for _, item in _iter_slots(candidate):
        f = _coerce_item(item, "formality", 1)
        try:
            formalities.append(int(f) if f is not None else 1)
        except (ValueError, TypeError):
            formalities.append(1)
    if len(formalities) < 2:
        return True
    return (max(formalities) - min(formalities)) <= 2


def check_pattern_clash(candidate: Any) -> bool:
    """Reject outfits combining two or more loud/statement patterns.

    1 loud pattern + solid/subtle is permitted.
    >= 2 loud patterns is a hard exclusion.
    """
    loud_count = 0
    for _, item in _iter_slots(candidate):
        pat = _normalize(_coerce_item(item, "pattern", "solid"))
        intensity = _normalize(_coerce_item(item, "pattern_intensity", ""))
        if intensity in ("loud", "bold", "high") or pat in LOUD_PATTERNS:
            loud_count += 1
            if loud_count >= 2:
                return False
    return True


def check_pairing_graph(candidate: Any, occasion: Any = None) -> bool:
    """Verify symmetric pairing constraints and forbidden edges.

    Forbidden edges:
    - Saree x athletic sneakers / running shoes / loafers / flip-flops.
    - Traditional ethnic sets (anarkali, lehenga_set, kurti_set, ethnic_set) x sneakers / loafers / flip-flops.
    - Ethnic bottoms (salwar, dhoti, churidar, lehenga_skirt) x sneakers / loafers.
    - Kurti x Western skirts (mini, midi, maxi skirt).
    - Kurti x sneakers / loafers.
    - Salwar / dhoti x Western tops (tshirt, tank, crop_top, hoodie, sweater, shirt_formal).
    - Layer over hoodie: strictly forbidden.
    - Layer over sweater: strictly forbidden EXCEPT blazer over fine-knit sweater.
    - Elegant looks (satin/silk/elegant crepe combinations) x sneakers / flip-flops.
    - Formal / wedding occasions x sneakers / loafers / flip-flops.
    - At most one layer garment.
    """
    slots = dict(_iter_slots(candidate))
    layer_count = sum(
        1
        for slot, item in slots.items()
        if slot == "layer" or _normalize(_coerce_item(item, "category", "")) in {"layer", "outer"}
    )
    if layer_count > 1:
        return False

    occ_norm = canonical_occasion(occasion) if occasion else ""

    top = slots.get("top")
    bottom = slots.get("bottom") or slots.get("ethnic_bottom")
    layer = slots.get("layer")
    shoes = slots.get("shoes")

    # 1. Layer over top restrictions
    if layer and top:
        top_sub = _normalize(_coerce_item(top, "sub_category", "") or _coerce_item(top, "subtype", "") or _coerce_item(top, "piece_id", "") or _coerce_item(top, "name", ""))
        layer_sub = _normalize(_coerce_item(layer, "sub_category", "") or _coerce_item(layer, "subtype", "") or _coerce_item(layer, "piece_id", "") or _coerce_item(layer, "name", ""))

        # Layer over hoodie is strictly rejected
        if "hoodie" in top_sub:
            return False

        # Layer over sweater is strictly rejected EXCEPT blazer over fine-knit sweater
        if "sweater" in top_sub or "knitwear" in top_sub:
            knit_gauge = _normalize(_coerce_item(top, "knit_gauge", "") or _coerce_item(top, "extra_knit_gauge", ""))
            is_fine = knit_gauge == "fine"
            is_blazer = "blazer" in layer_sub
            if not (is_blazer and is_fine):
                return False

    # 2. Kurti + Western skirt restriction
    if top:
        top_sub = _normalize(_coerce_item(top, "sub_category", "") or _coerce_item(top, "subtype", "") or _coerce_item(top, "piece_id", "") or _coerce_item(top, "name", ""))
        top_role = _normalize(_coerce_item(top, "role", ""))
        is_kurti = "kurti" in top_sub or "kurta" in top_sub or top_role == "ethnic_top"

        if is_kurti and bottom:
            bot_sub = _normalize(_coerce_item(bottom, "sub_category", "") or _coerce_item(bottom, "subtype", "") or _coerce_item(bottom, "piece_id", "") or _coerce_item(bottom, "name", ""))
            bot_role = _normalize(_coerce_item(bottom, "role", ""))
            # Western skirt forbidden with kurti
            if "skirt" in bot_sub and "ethnic" not in bot_sub and "lehenga" not in bot_sub and bot_role != "lehenga_separate":
                return False

    # 3. Salwar / dhoti + Western top restriction
    if bottom:
        bot_sub = _normalize(_coerce_item(bottom, "sub_category", "") or _coerce_item(bottom, "subtype", "") or _coerce_item(bottom, "piece_id", "") or _coerce_item(bottom, "name", ""))
        is_salwar = "salwar" in bot_sub or "dhoti" in bot_sub or "churidar" in bot_sub
        if is_salwar and top:
            top_sub = _normalize(_coerce_item(top, "sub_category", "") or _coerce_item(top, "subtype", "") or _coerce_item(top, "piece_id", "") or _coerce_item(top, "name", ""))
            top_role = _normalize(_coerce_item(top, "role", ""))
            is_ethnic_top = "kurti" in top_sub or "kurta" in top_sub or "tunic" in top_sub or top_role in ("ethnic_top", "blouse") or "blouse" in top_sub
            if not is_ethnic_top:
                return False

    # 4. Footwear restrictions
    if shoes:
        shoe_sub = _normalize(
            _coerce_item(shoes, "sub_category", "")
            or _coerce_item(shoes, "subtype", "")
            or _coerce_item(shoes, "piece_id", "")
            or _coerce_item(shoes, "name", "")
        )
        is_sneaker = "sneaker" in shoe_sub or "running" in shoe_sub or "trainer" in shoe_sub
        is_loafer = "loafer" in shoe_sub
        is_flip_flop = "flip_flop" in shoe_sub or "thong" in shoe_sub or "slide" in shoe_sub

        # Forbidden in wedding or formal
        if occ_norm in ("wedding", "formal"):
            if is_sneaker or is_loafer or is_flip_flop:
                return False

        has_satin_or_silk = False
        has_elegant_vibe = False

        for slot, item in slots.items():
            if slot == "shoes":
                continue
            cat = _normalize(_coerce_item(item, "category", ""))
            sub = _normalize(
                _coerce_item(item, "sub_category", "")
                or _coerce_item(item, "subtype", "")
                or _coerce_item(item, "piece_id", "")
                or _coerce_item(item, "name", "")
            )
            role = _normalize(_coerce_item(item, "role", ""))
            f = int(_coerce_item(item, "formality", 1) or 1)
            fabric = _normalize(_coerce_item(item, "fabric", ""))
            vibes = _normalize(_coerce_item(item, "vibes", "") or _coerce_item(item, "style_tags", "") or "")

            if fabric in ("satin", "silk"):
                has_satin_or_silk = True
            if "elegant" in vibes and f >= 3:
                has_elegant_vibe = True

            # Saree: NEVER sneakers, loafers, or flip-flops
            if cat == "saree" or sub == "saree" or role == "saree":
                if is_sneaker or is_loafer or is_flip_flop:
                    return False

            # Traditional sets (anarkali, lehenga_set, kurti_set, ethnic_set): NEVER sneakers or loafers
            if cat == "ethnic_set" or sub in ("anarkali", "kurta_set", "kurti_set", "lehenga_set", "sharara_set") or role == "ethnic_set":
                if is_sneaker or is_loafer or is_flip_flop:
                    return False

            # Traditional ethnic bottoms (salwar, dhoti, churidar, lehenga_skirt): NEVER sneakers or loafers
            if sub in ("salwar", "dhoti", "churidar", "lehenga_skirt") or role in ("ethnic_bottom", "lehenga_separate"):
                if sub == "lehenga_skirt" and f <= 2 and occ_norm in ("casual", "college"):
                    pass
                else:
                    if is_sneaker or is_loafer or is_flip_flop:
                        return False

            # Kurti: NEVER sneakers or loafers
            if "kurti" in sub or "kurta" in sub or role == "ethnic_top":
                if is_sneaker or is_loafer:
                    return False

            # Formal suit / tuxedo forbidden with flip-flops
            if f >= 4 and is_flip_flop:
                return False

        # Elegant looks with satin/silk or elegant styling: NEVER sneakers or flip-flops
        if (has_satin_or_silk or has_elegant_vibe) and (is_sneaker or is_flip_flop):
            return False

    # 5. Saree companion requirement
    saree = slots.get("saree")
    if saree:
        inc_blouse = _coerce_item(saree, "includes_blouse", None)
        if inc_blouse is False and "top" not in slots:
            return False

    return True


def evaluate_pairing_strength(candidate: Any) -> float:
    """Compute structural pairing strength score in [0.0, 1.0].

    Core pairings: 1.0 (e.g. saree + heels/juttis, top + bottom + clean shoes)
    Stretch pairings: 0.70 (e.g. blazer + casual sneakers, lehenga skirt + sneakers)
    Neutral / standard: 0.85
    Forbidden: 0.0
    """
    slots = dict(_iter_slots(candidate))
    if not slots:
        return 0.5

    shoes = slots.get("shoes")
    if not shoes:
        return 0.80

    shoe_sub = _normalize(
        _coerce_item(shoes, "sub_category", "") or _coerce_item(shoes, "subtype", "") or ""
    )
    is_sneaker = "sneaker" in shoe_sub or "running" in shoe_sub

    for slot, item in slots.items():
        if slot == "shoes":
            continue
        sub = _normalize(
            _coerce_item(item, "sub_category", "") or _coerce_item(item, "subtype", "") or ""
        )
        cat = _normalize(_coerce_item(item, "category", ""))
        f = int(_coerce_item(item, "formality", 1) or 1)
        if ("lehenga" in sub or "lehenga" in cat) and f <= 2 and is_sneaker:
            return 0.70  # Stretch fusion
        if ("blazer" in sub or "blazer" in cat) and is_sneaker and f <= 3:
            return 0.75  # Smart casual stretch

    return 0.90


def hard_filter_candidate(
    candidate: Any,
    occasion: Any,
    season: Any,
) -> bool:
    """Apply hard filters: availability, duplicates, bottom count, season,
    formality spread, pattern clash, pairing graph, and occasion compatibility.

    Returns True if the candidate passes all filters.
    """
    for _, item in _iter_slots(candidate):
        if not is_item_available(item):
            return False
        if not season_match(item, season):
            return False
        if not item_occasion_match(item, occasion):
            return False

    if duplicate_items(candidate):
        return False
    if not no_two_bottoms(candidate):
        return False
    if not check_formality_spread(candidate):
        return False
    if not check_pattern_clash(candidate):
        return False
    if not check_pairing_graph(candidate, occasion):
        return False
    if not no_formal_shoes_for_lounge(candidate, occasion):
        return False
    if not no_sneakers_with_ethnic_formal(candidate, occasion):
        return False
    return True

