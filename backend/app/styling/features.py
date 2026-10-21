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
    """Collect colour values for palette scoring."""
    colors: list[Any] = []
    for item in items:
        color = _coerce_item(item, "color", None)
        if color is not None:
            colors.append(color)
        color_tags = _coerce_item(item, "colors", None) or _coerce_item(item, "color_tags", None)
        if isinstance(color_tags, (list, tuple)):
            for ct in color_tags:
                if ct and ct not in colors:
                    colors.append(ct)
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


STYLE_ARCHETYPES: dict[str, set[str]] = {
    "casual": {"casual", "streetwear", "minimal", "relaxed", "comfort", "daily"},
    "classic": {"classic", "minimal", "quiet_luxury", "tailored", "workwear", "smart_casual"},
    "ethnic": {"traditional", "festive", "ethnic", "artisanal", "regal", "contemporary"},
    "formal": {"formal", "power_dressing", "elegant", "classic", "minimal"},
    "party": {"party", "glam", "elegant", "90s_chic", "playful"},
    "boho": {"boho", "bohemian", "artisanal", "relaxed", "feminine"},
}


def style_feature_score(candidate: Any) -> float:
    """Score aesthetic coherence and harmony across outfit pieces.

    Rewards outfits whose pieces belong to harmonious style archetypes or share
    tags, penalising disjointed or clashing combinations.
    """
    items = _extract_items(candidate)
    if not items:
        return 0.5
    item_styles: list[set[str]] = []
    for item in items:
        s_tags: set[str] = set()
        for key in ("style", "styles", "style_tags"):
            val = _coerce_item(item, key, None)
            if isinstance(val, (list, tuple, set)):
                s_tags.update(str(v).strip().lower() for v in val if v)
            elif isinstance(val, str) and val.strip():
                s_tags.add(val.strip().lower())
        if s_tags:
            item_styles.append(s_tags)

    if len(item_styles) <= 1:
        return 0.85

    # Check for direct shared tag across all or pairwise
    common = set.intersection(*item_styles)
    if common:
        return 1.0

    # Check archetype overlap
    archetype_matches = 0
    total_pairs = 0
    has_traditional = any("traditional" in s or "ethnic" in s or "regal" in s for s in item_styles)
    has_streetwear = any("streetwear" in s or "sporty" in s for s in item_styles)

    for i in range(len(item_styles)):
        for j in range(i + 1, len(item_styles)):
            total_pairs += 1
            pair_a = item_styles[i]
            pair_b = item_styles[j]
            # If they share any tag
            if pair_a & pair_b:
                archetype_matches += 1
            else:
                # Check if both match any archetype
                matched_arch = any(
                    bool(pair_a & arch_tags) and bool(pair_b & arch_tags)
                    for arch_tags in STYLE_ARCHETYPES.values()
                )
                if matched_arch:
                    archetype_matches += 1

    base_coherence = (archetype_matches / max(1, total_pairs))
    score = 0.5 + (0.5 * base_coherence)

    # Moderate clash penalty for combining pure traditional with sporty/streetwear
    if has_traditional and has_streetwear:
        score = max(0.35, score - 0.25)

    return round(score, 3)


def occasion_feature_score(candidate: Any, occasion: Any) -> float:
    """Score how well item formality and occasion affinities match the target occasion."""
    target_band = occasion_to_formality_band(occasion)
    target_name = str(occasion).strip().lower()
    if isinstance(candidate, dict):
        slots = _coerce_item(candidate, "slots", {})
    else:
        slots = getattr(candidate, "slots", {})
    scores: list[float] = []
    for item in slots.values():
        formality = int(_coerce_item(item, "formality", 1) or 1)
        formality_score = 1.0 if formality <= target_band else 0.3

        item_occs = _coerce_item(item, "occasions", None)
        if item_occs is None:
            occ = _coerce_item(item, "occasion", None)
            item_occs = [occ] if occ else []
        elif isinstance(item_occs, str):
            item_occs = [item_occs]

        if item_occs:
            norm_occs = {str(o).strip().lower() for o in item_occs if o}
            if target_name in norm_occs or "all" in norm_occs or "all_season" in norm_occs:
                occ_score = 1.0
            else:
                occ_score = 0.4
        else:
            occ_score = 0.8

        scores.append(round(0.4 * formality_score + 0.6 * occ_score, 3))
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
