"""Feature scoring for outfit ranking.

Ported from StyleSenseAI outfits/features.py — uses local body_fit and color
modules so the engine stays I/O-free.

Body guidance is neutral and optional: when no body_shape is provided,
the body_fit feature defaults to 0.5 (neutral) and does not penalise.
"""

from __future__ import annotations

from typing import Any

from app.styling.body_fit import body_fit
from app.styling.color import palette_harmony
from app.styling.rules import (
    OUTFIT_RULE_CONFIG,
    occasion_to_formality_band,
    season_match,
)


def _coerce_item(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, item.get(key.replace("_", ""), default))
    return getattr(item, key, default)


def _extract_items(candidate: Any) -> list[Any]:
    """Get the list of items from a candidate's slots."""
    if isinstance(candidate, dict):
        return list(_coerce_item(candidate, "slots", {}).values())
    return list(getattr(candidate, "slots", {}).values())


def _extract_colors(items: list[Any]) -> list[Any]:
    """Collect colour values and pattern colours for palette scoring."""
    colors: list[Any] = []
    for item in items:
        color = _coerce_item(item, "color", None)
        if color is not None:
            colors.append(color)
        pattern = _coerce_item(item, "pattern", None)
        if pattern is not None:
            colors.append(pattern)
    return colors


# -----------------------------------------------------------------------
# Individual feature scores (each returns 0..1)
# -----------------------------------------------------------------------


def body_feature_score(
    candidate: Any,
    shape: str | None = None,
    attrs: dict[str, Any] | None = None,
) -> float:
    """Score body-fit compatibility. Neutral (0.5) when shape is absent."""
    if not shape:
        return 0.5
    items = _extract_items(candidate)
    if not items:
        return 0.5
    attr_map = dict(attrs) if attrs else {}
    if not attr_map:
        for item in items:
            for key in ("neckline", "fit", "length", "rise", "subcategory"):
                value = _coerce_item(item, key, None)
                if value is not None:
                    attr_map[key] = value
    return body_fit(attr_map, shape, source="manual")


def color_feature_score(candidate: Any) -> float:
    """Score palette harmony across the outfit's colours."""
    items = _extract_items(candidate)
    return palette_harmony(_extract_colors(items))


def style_feature_score(candidate: Any) -> float:
    """Reward stylistic diversity within an outfit."""
    items = _extract_items(candidate)
    if not items:
        return 0.5
    styles: list[str] = []
    for item in items:
        style = _coerce_item(item, "style", None)
        if style is not None:
            styles.append(str(style).lower())
    if not styles:
        return 0.5
    unique = set(styles)
    return round(len(unique) / max(1, len(styles)), 3)


def occasion_feature_score(candidate: Any, occasion: Any) -> float:
    """Score how well item formality levels match the target occasion."""
    target = occasion_to_formality_band(occasion)
    if isinstance(candidate, dict):
        slots = _coerce_item(candidate, "slots", {})
    else:
        slots = getattr(candidate, "slots", {})
    scores: list[float] = []
    for item in slots.values():
        formality = int(_coerce_item(item, "formality", 1) or 1)
        scores.append(1.0 if formality <= target else 0.3)
    return round(sum(scores) / max(1, len(scores)), 3) if scores else 0.5


def season_feature_score(candidate: Any, season: Any) -> float:
    """Score seasonal compatibility across all items."""
    items = _extract_items(candidate)
    if not items:
        return 0.5
    valid = [1.0 if season_match(item, season) else 0.0 for item in items]
    return round(sum(valid) / len(valid), 3)


def layering_feature_score(candidate: Any) -> float:
    """Reward outfits that include layering pieces or dupatta."""
    items = _extract_items(candidate)
    layered = sum(
        1
        for item in items
        if _coerce_item(item, "category") in {"layer", "dupatta"}
    )
    return 1.0 if layered else 0.5


def novelty_feature_score(candidate: Any) -> float:
    """Average the per-item novelty values (defaults to 0.5)."""
    items = _extract_items(candidate)
    if not items:
        return 0.5
    novelty_values: list[float] = []
    for item in items:
        novelty = _coerce_item(item, "novelty", 0.5)
        novelty_values.append(float(novelty))
    return round(sum(novelty_values) / len(novelty_values), 3)


# -----------------------------------------------------------------------
# Aggregate scoring
# -----------------------------------------------------------------------


def feature_scores(
    candidate: Any,
    *,
    occasion: Any,
    season: Any,
    body_shape: str | None = None,
    attrs: dict[str, Any] | None = None,
    seed: int | None = None,
) -> dict[str, float]:
    """Return the weighted component scores for a candidate outfit."""
    return {
        "body_fit": body_feature_score(candidate, body_shape, attrs),
        "color": color_feature_score(candidate),
        "style": style_feature_score(candidate),
        "occasion": occasion_feature_score(candidate, occasion),
        "season": season_feature_score(candidate, season),
        "layering": layering_feature_score(candidate),
        "novelty": novelty_feature_score(candidate),
    }


def score_outfit(
    candidate: Any,
    *,
    occasion: Any,
    season: Any,
    body_shape: str | None = None,
    attrs: dict[str, Any] | None = None,
    seed: int | None = None,
) -> float:
    """Weighted aggregate score for a candidate outfit.

    Uses the config-driven weights from ``OUTFIT_RULE_CONFIG``.
    """
    values = feature_scores(
        candidate,
        occasion=occasion,
        season=season,
        body_shape=body_shape,
        attrs=attrs,
        seed=seed,
    )
    weights = OUTFIT_RULE_CONFIG["weights"]
    numerator = sum(
        weights.get(name, 0.0) * value for name, value in values.items()
    )
    denominator = sum(weights.values())
    return round(numerator / denominator, 3) if denominator else 0.5
