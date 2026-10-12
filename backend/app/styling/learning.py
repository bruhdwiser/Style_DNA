"""Style DNA and transparent preference affinity calculations.

Ported and adapted from StyleSenseAI styling/learning.py.
Deterministic, pure Python, and explainable:
- No neural networks, computer vision, or black-box models.
- Transparent weighted event tallies:
    wear: +3.0 (strongest intent: worn in real life)
    save: +2.0 (high intent: bookmarked)
    like: +1.0 (positive reaction)
    skip: -0.5 (mild disinterest)
    dislike: -2.0 (negative reaction)
- Bounded ranking influence:
    Affinity adjustments are capped to at most +/-0.08 so outfit validity
    and occasion rules always strictly dominate.
"""

from __future__ import annotations

import math
from typing import Any

# Event weighting scale
EVENT_WEIGHTS: dict[str, float] = {
    "wear": 3.0,
    "save": 2.0,
    "like": 1.0,
    "skip": -0.5,
    "dislike": -2.0,
}

# Maximum influence on outfit score (strictly bounded so occasion/validity rules dominate)
MAX_AFFINITY_INFLUENCE: float = 0.08


def _coerce_item(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, item.get(key.replace("_", ""), default))
    return getattr(item, key, default)


def _sigmoid_normalize(raw_score: float, scale: float = 3.0) -> float:
    """Map raw cumulative tally into a stable 0.0..1.0 range centered at 0.5 (neutral)."""
    # 0 raw -> 0.5 neutral
    # +3 raw (1 wear or 3 likes) -> ~0.73
    # +6 raw -> ~0.88
    # -3 raw -> ~0.27
    try:
        val = 1.0 / (1.0 + math.exp(-raw_score / scale))
        return round(val, 3)
    except OverflowError:
        return 1.0 if raw_score > 0 else 0.0


def calculate_affinities(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate normalized tag, color, and category affinities from raw event logs.

    Pure, deterministic function: identical events produce identical affinities.
    """
    event_counts: dict[str, int] = {
        "like": 0,
        "dislike": 0,
        "save": 0,
        "skip": 0,
        "wear": 0,
    }

    raw_color_scores: dict[str, float] = {}
    raw_category_scores: dict[str, float] = {}
    raw_style_scores: dict[str, float] = {}

    for ev in events:
        ev_type = str(ev.get("event_type", "")).lower()
        if ev_type in event_counts:
            event_counts[ev_type] += 1
        else:
            continue

        weight = EVENT_WEIGHTS.get(ev_type, 0.0)
        meta = ev.get("metadata") or {}

        # Colors
        colors = meta.get("colors") or []
        if isinstance(colors, str):
            colors = [colors]
        primary_color = meta.get("primary_color")
        if primary_color and primary_color not in colors:
            colors.append(primary_color)
        for c in colors:
            clean_c = str(c).strip().lower()
            if clean_c:
                raw_color_scores[clean_c] = raw_color_scores.get(clean_c, 0.0) + weight

        # Categories / Slots
        categories = meta.get("categories") or []
        if isinstance(categories, str):
            categories = [categories]
        for cat in categories:
            clean_cat = str(cat).strip().lower()
            if clean_cat:
                raw_category_scores[clean_cat] = raw_category_scores.get(clean_cat, 0.0) + weight

        # Styles / Tags
        styles = meta.get("styles") or meta.get("style_tags") or []
        if isinstance(styles, str):
            styles = [styles]
        for s in styles:
            clean_s = str(s).strip().lower()
            if clean_s:
                raw_style_scores[clean_s] = raw_style_scores.get(clean_s, 0.0) + weight

    # Normalize into 0.0..1.0 where 0.5 is neutral
    normalized_colors = {
        k: _sigmoid_normalize(v) for k, v in sorted(raw_color_scores.items(), key=lambda x: -x[1])
    }
    normalized_categories = {
        k: _sigmoid_normalize(v) for k, v in sorted(raw_category_scores.items(), key=lambda x: -x[1])
    }
    normalized_styles = {
        k: _sigmoid_normalize(v) for k, v in sorted(raw_style_scores.items(), key=lambda x: -x[1])
    }

    # Extract top positive preferences (> 0.55) and avoidances (< 0.45)
    top_preferences = []
    avoidances = []

    for name, score in normalized_colors.items():
        if score >= 0.55:
            top_preferences.append({"dimension": "color", "name": name.title(), "score": score})
        elif score <= 0.45:
            avoidances.append({"dimension": "color", "name": name.title(), "score": score})

    for name, score in normalized_styles.items():
        if score >= 0.55:
            top_preferences.append({"dimension": "style", "name": name.title(), "score": score})
        elif score <= 0.45:
            avoidances.append({"dimension": "style", "name": name.title(), "score": score})

    for name, score in normalized_categories.items():
        if score >= 0.55:
            top_preferences.append({"dimension": "category", "name": name.title(), "score": score})
        elif score <= 0.45:
            avoidances.append({"dimension": "category", "name": name.title(), "score": score})

    top_preferences.sort(key=lambda x: -x["score"])
    avoidances.sort(key=lambda x: x["score"])

    return {
        "total_events": len(events),
        "event_counts": event_counts,
        "affinities": {
            "colors": normalized_colors,
            "categories": normalized_categories,
            "styles": normalized_styles,
        },
        "top_preferences": top_preferences[:10],
        "avoidances": avoidances[:10],
        "influence_cap": MAX_AFFINITY_INFLUENCE,
    }


def compute_outfit_affinity_adjustment(
    candidate: Any,
    affinities: dict[str, Any],
) -> tuple[float, list[str]]:
    """Compute bounded score delta for a candidate outfit based on Style DNA.

    Returns:
        (delta, matching_reasons):
            delta: float in [-MAX_AFFINITY_INFLUENCE, +MAX_AFFINITY_INFLUENCE]
            matching_reasons: list of explainable attribute references
    """
    if not affinities or not affinities.get("total_events"):
        return 0.0, []

    aff_map = affinities.get("affinities") or {}
    colors_map = aff_map.get("colors") or {}
    styles_map = aff_map.get("styles") or {}
    cats_map = aff_map.get("categories") or {}

    if isinstance(candidate, dict):
        slots = _coerce_item(candidate, "slots", {})
    else:
        slots = getattr(candidate, "slots", {})

    items = list(slots.values())
    if not items:
        return 0.0, []

    item_deltas: list[float] = []
    liked_traits: list[str] = []
    disliked_traits: list[str] = []

    for item in items:
        # Check color
        color = str(_coerce_item(item, "color", "")).strip().lower()
        if color and color in colors_map:
            val = colors_map[color]
            diff = val - 0.5  # [-0.5, +0.5]
            item_deltas.append(diff)
            if val >= 0.60 and color.title() not in liked_traits:
                liked_traits.append(color.title())
            elif val <= 0.40 and color.title() not in disliked_traits:
                disliked_traits.append(color.title())

        # Check category
        cat = str(_coerce_item(item, "category", "")).strip().lower()
        if cat and cat in cats_map:
            val = cats_map[cat]
            diff = val - 0.5
            item_deltas.append(diff)

        # Check styles
        style = str(_coerce_item(item, "style", "")).strip().lower()
        if style and style in styles_map:
            val = styles_map[style]
            diff = val - 0.5
            item_deltas.append(diff)
            if val >= 0.60 and style.title() not in liked_traits:
                liked_traits.append(style.title())
            elif val <= 0.40 and style.title() not in disliked_traits:
                disliked_traits.append(style.title())

    if not item_deltas:
        return 0.0, []

    avg_diff = sum(item_deltas) / len(item_deltas)
    # Scale avg_diff (which is in [-0.5, +0.5]) into [-MAX_AFFINITY_INFLUENCE, +MAX_AFFINITY_INFLUENCE]
    raw_delta = (avg_diff / 0.5) * MAX_AFFINITY_INFLUENCE
    bounded_delta = max(-MAX_AFFINITY_INFLUENCE, min(MAX_AFFINITY_INFLUENCE, raw_delta))
    rounded_delta = round(bounded_delta, 3)

    reasons: list[str] = []
    if rounded_delta > 0.01:
        trait_desc = ", ".join(liked_traits[:3]) if liked_traits else "your preferred attributes"
        reasons.append(
            f"Style DNA affinity added +{rounded_delta:.2f} based on affinity for {trait_desc}."
        )
    elif rounded_delta < -0.01:
        trait_desc = ", ".join(disliked_traits[:3]) if disliked_traits else "disliked attributes"
        reasons.append(
            f"Style DNA affinity adjusted {rounded_delta:.2f} based on feedback for {trait_desc}."
        )

    return rounded_delta, reasons
