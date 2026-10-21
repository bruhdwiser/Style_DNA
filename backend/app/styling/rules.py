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
    "plaid_wide",
    "abstract_bold",
    "camo",
    "chevron",
    "tie_dye",
    "paisley_bold",
})


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
    """Reject formal shoes when the intended outfit is lounge-oriented."""
    if occasion_to_formality_band(occasion) > 1:
        return True
    for _, item in _iter_slots(candidate):
        category = _coerce_item(item, "category")
        if category == "shoes":
            formality = _coerce_item(item, "formality", 1) or 1
            try:
                formality_value = int(formality)
            except (TypeError, ValueError):
                formality_value = 1
            if formality_value > 1:
                return False
    return True


def item_occasion_match(item: Any, occasion: Any) -> bool:
    """Check whether an item is valid for a target occasion.

    Items without occasion tags are treated as versatile.
    If occasion tags are present, the target occasion must match or fall into
    a compatible occasion cluster.
    """
    if not occasion:
        return True
    target = _normalize(occasion)
    if target in ("all", "any", "all_occasion"):
        return True

    occasions = _coerce_item(item, "occasions", None)
    if occasions is None:
        occ = _coerce_item(item, "occasion", None)
        if occ is not None:
            occasions = [occ]

    if not occasions:
        return True

    if isinstance(occasions, str):
        normalized_options = {_normalize(occasions)}
    elif isinstance(occasions, (list, tuple, set)):
        normalized_options = {_normalize(o) for o in occasions if o}
    else:
        normalized_options = {_normalize(occasions)}

    if not normalized_options or "all" in normalized_options or "all_season" in normalized_options:
        return True

    if target in normalized_options:
        return True

    clusters = {
        "casual": {"casual", "college", "lounge", "daily"},
        "college": {"college", "casual"},
        "lounge": {"lounge", "casual"},
        "work": {"work", "formal", "office", "classic"},
        "formal": {"formal", "work", "wedding", "festive"},
        "festive": {"festive", "wedding", "traditional", "party", "formal"},
        "wedding": {"wedding", "festive", "traditional", "formal"},
        "party": {"party", "date", "date_night", "festive", "casual"},
        "date": {"date", "date_night", "party", "casual", "work"},
    }
    allowed = clusters.get(target, {target})
    if bool(normalized_options & allowed):
        return True

    # Allow shoes/layers with matching formality or style
    style = _normalize(_coerce_item(item, "style", ""))
    formality = int(_coerce_item(item, "formality", 1) or 1)
    if target in {"wedding", "festive", "formal"} and (style in {"formal", "festive", "traditional"} or formality >= 2):
        return True

    return False


def no_sneakers_with_ethnic_formal(candidate: Any, occasion: Any) -> bool:
    """Reject casual sneakers with traditional ethnic formal looks (anarkali/saree/ethnic_set)."""
    target = _normalize(occasion)
    # Wedding / festive strictly rejects athletic/streetwear sneakers with formal ethnic sets
    if target in {"wedding", "festive", "formal"}:
        has_formal_ethnic = False
        has_sneakers = False
        for _, item in _iter_slots(candidate):
            cat = _normalize(_coerce_item(item, "category", ""))
            subcat = _normalize(_coerce_item(item, "sub_category", "") or _coerce_item(item, "subtype", ""))
            if cat in {"saree", "ethnic_set"} or subcat in {"anarkali", "saree", "anarkali_set", "sharara_set"}:
                has_formal_ethnic = True
            if cat == "shoes" and ("sneaker" in subcat or "sneakers" in subcat):
                has_sneakers = True
        if has_formal_ethnic and has_sneakers:
            return False

    # Conversely, for pure casual, reject exclusive wedding/bridal items
    if target in {"casual", "college", "lounge"}:
        for _, item in _iter_slots(candidate):
            subcat = _normalize(_coerce_item(item, "sub_category", "") or _coerce_item(item, "subtype", ""))
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
    - Saree x athletic sneakers / running shoes / flip flops.
    - Traditional ethnic sets (formality >= 3 or wedding/festive) x athletic sneakers.
    - High-formality lehengas (formality >= 4 or wedding) x sneakers.
    - Formal blazers/suits x gym flip-flops.
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

    occ_norm = _normalize(occasion) if occasion else ""

    shoes = slots.get("shoes")
    if shoes:
        shoe_cat = _normalize(_coerce_item(shoes, "category", ""))
        shoe_sub = _normalize(
            _coerce_item(shoes, "sub_category", "")
            or _coerce_item(shoes, "subtype", "")
            or _coerce_item(shoes, "name", "")
        )
        is_sneaker = "sneaker" in shoe_sub or "running" in shoe_sub or "trainer" in shoe_sub
        is_flip_flop = "flip_flop" in shoe_sub or "thong" in shoe_sub

        for slot, item in slots.items():
            if slot == "shoes":
                continue
            cat = _normalize(_coerce_item(item, "category", ""))
            sub = _normalize(
                _coerce_item(item, "sub_category", "")
                or _coerce_item(item, "subtype", "")
                or _coerce_item(item, "name", "")
            )
            f = int(_coerce_item(item, "formality", 1) or 1)

            # Saree forbidden with sneakers or flip-flops
            if cat == "saree" or sub == "saree":
                if is_sneaker or is_flip_flop:
                    return False

            # Ethnic set with formality >= 3 or wedding/festive forbidden with sneakers
            if (cat == "ethnic_set" or sub in ("anarkali", "kurta_set", "sharara")) and (
                f >= 3 or occ_norm in ("wedding", "festive")
            ):
                if is_sneaker or is_flip_flop:
                    return False

            # High formality lehengas (f >= 4 or wedding) forbidden with sneakers
            if ("lehenga" in sub or "lehenga" in cat) and (f >= 4 or occ_norm == "wedding"):
                if is_sneaker or is_flip_flop:
                    return False

            # Formal suit / tuxedo forbidden with flip-flops
            if f >= 4 and is_flip_flop:
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
        if _coerce_item(item, "is_available", True) is False:
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

