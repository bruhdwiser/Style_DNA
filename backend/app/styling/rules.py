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
        "body_fit": 0.26,
        "color": 0.20,
        "style": 0.16,
        "occasion": 0.14,
        "season": 0.12,
        "layering": 0.06,
        "novelty": 0.06,
    },
    "hard_filter_limits": {
        "max_bottoms": 1,
        "lounge_formal_shoes_max": 1,
    },
}


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


def hard_filter_candidate(
    candidate: Any,
    occasion: Any,
    season: Any,
) -> bool:
    """Apply hard filters: availability, duplicates, bottom count, season,
    and occasion compatibility.

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
    if not no_formal_shoes_for_lounge(candidate, occasion):
        return False
    if not no_sneakers_with_ethnic_formal(candidate, occasion):
        return False
    return True

