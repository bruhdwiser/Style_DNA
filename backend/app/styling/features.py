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
    evaluate_pairing_strength,
)
from app.styling.skeletons import CORE_SLOTS


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


PARTIAL_VIBE_SYNONYMS: dict[str, set[str]] = {
    "minimal": {"clean", "simple", "monochrome"},
    "classic": {"tailored", "smart_casual", "workwear", "structured"},
    "streetwear": {"oversized", "hoodie", "skate", "urban"},
    "elegant": {"chic", "luxurious", "graceful", "evening"},
    "bohemian": {"boho", "artisanal"},
    "romantic": {"soft", "lace"},
}


def vibe_feature_score(
    candidate: Any,
    vibe: str | None = None,
    vibes: list[str] | None = None,
) -> float:
    """Score multi-label aesthetic vibe affinity across outfit pieces.

    Direct matches to selected vibes give 1.0; narrow aesthetic synonyms give 0.45;
    unmatched items give 0.0. Core garments establish 75% of the aesthetic statement,
    while peripheral pieces provide complementary polish (25%).
    """
    target_vibes: list[str] = []
    if vibe and str(vibe).strip():
        target_vibes.append(str(vibe).strip().lower())
    if vibes:
        for v in vibes:
            v_clean = str(v).strip().lower()
            if v_clean and v_clean not in target_vibes:
                target_vibes.append(v_clean)

    if not target_vibes:
        return 0.80

    if isinstance(candidate, dict):
        slots = _coerce_item(candidate, "slots", candidate)
    else:
        slots = getattr(candidate, "slots", {})

    if not isinstance(slots, dict) or not slots:
        items = _extract_items(candidate)
        if not items:
            return 0.50
        slots = {f"slot_{i}": it for i, it in enumerate(items)}

    core_scores: list[float] = []
    peri_scores: list[float] = []

    for slot, item in slots.items():
        item_vibes: set[str] = set()
        for key in ("vibes", "vibe", "style_tags", "styles", "style"):
            val = _coerce_item(item, key, None)
            if isinstance(val, (list, tuple, set)):
                item_vibes.update(str(v).strip().lower() for v in val if v)
            elif isinstance(val, str) and val.strip():
                item_vibes.update(str(v).strip().lower() for v in val.replace("|", ",").split(",") if v.strip())

        best_match = 0.0
        for tv in target_vibes:
            if tv in item_vibes:
                best_match = 1.0
                break
            partials = PARTIAL_VIBE_SYNONYMS.get(tv, set())
            if item_vibes & partials:
                best_match = max(best_match, 0.45)

        if slot in CORE_SLOTS:
            core_scores.append(best_match)
        else:
            peri_scores.append(best_match)

    if core_scores and peri_scores:
        core_avg = sum(core_scores) / len(core_scores)
        peri_avg = sum(peri_scores) / len(peri_scores)
        score = 0.75 * core_avg + 0.25 * peri_avg
    elif core_scores:
        score = sum(core_scores) / len(core_scores)
    elif peri_scores:
        score = sum(peri_scores) / len(peri_scores)
    else:
        score = 0.50

    return round(score, 3)


def formality_fit_score(candidate: Any) -> float:
    """Score harmony within the allowed formality spread."""
    items = _extract_items(candidate)
    if len(items) < 2:
        return 0.90
    formalities: list[int] = []
    for item in items:
        f = _coerce_item(item, "formality", 1)
        try:
            formalities.append(int(f) if f is not None else 1)
        except (ValueError, TypeError):
            formalities.append(1)
    spread = max(formalities) - min(formalities)
    if spread == 0:
        return 1.0
    elif spread == 1:
        return 0.90
    elif spread == 2:
        return 0.75
    return 0.20


def freshness_feature_score(candidate: Any) -> float:
    """Novelty and freshness score (neutral 0.50 when no wear history)."""
    items = _extract_items(candidate)
    if not items:
        return 0.50
    novelties = []
    for item in items:
        n = _coerce_item(item, "novelty", None)
        if n is not None:
            try:
                novelties.append(float(n))
            except (ValueError, TypeError):
                pass
    if not novelties:
        return 0.50
    return round(max(0.0, min(1.0, sum(novelties) / len(novelties))), 3)


def novelty_feature_score(candidate: Any) -> float:
    """Backward-compatible alias for freshness score."""
    return freshness_feature_score(candidate)


# -----------------------------------------------------------------------
# Aggregate scoring
# -----------------------------------------------------------------------


def feature_scores(
    candidate: Any,
    *,
    occasion: Any,
    season: Any,
    vibe: str | None = None,
    vibes: list[str] | None = None,
    body_shape: str | None = None,
    attrs: dict[str, Any] | None = None,
    seed: int | None = None,
) -> dict[str, float]:
    """Return the weighted component scores for a candidate outfit."""
    occ_score = occasion_feature_score(candidate, occasion)
    pair_score = evaluate_pairing_strength(candidate)
    color_score = color_feature_score(candidate)
    style_score = style_feature_score(candidate)
    vibe_score = vibe_feature_score(candidate, vibe=vibe, vibes=vibes)
    formality_score = formality_fit_score(candidate)
    season_score = season_feature_score(candidate, season)
    freshness_score = freshness_feature_score(candidate)
    layer_score = layering_feature_score(candidate)
    style_dna_score = 0.50

    return {
        # Normalized target features
        "occasion_fit": occ_score,
        "pairing_strength": pair_score,
        "color_harmony": color_score,
        "style_coherence": style_score,
        "vibe_affinity": vibe_score,
        "formality_fit": formality_score,
        "season_fit": season_score,
        "freshness": freshness_score,
        "style_dna": style_dna_score,
        "layering": layer_score,
        "body_fit": 0.50,  # Neutral, 0.00 weight in score
        # Legacy aliases for backward compatibility with tests/explainers
        "color": color_score,
        "style": style_score,
        "occasion": occ_score,
        "season": season_score,
        "novelty": freshness_score,
    }


def score_outfit(
    candidate: Any,
    *,
    occasion: Any,
    season: Any,
    vibe: str | None = None,
    vibes: list[str] | None = None,
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
        vibe=vibe,
        vibes=vibes,
        body_shape=body_shape,
        attrs=attrs,
        seed=seed,
    )
    has_target_vibe = bool((vibe and str(vibe).strip()) or (vibes and any(str(v).strip() for v in vibes)))
    if has_target_vibe:
        weights = {
            "occasion_fit": 0.18,
            "vibe_affinity": 0.20,
            "pairing_strength": 0.16,
            "color_harmony": 0.14,
            "style_coherence": 0.12,
            "formality_fit": 0.08,
            "season_fit": 0.06,
            "freshness": 0.03,
            "style_dna": 0.02,
            "layering": 0.01,
        }
    else:
        weights = OUTFIT_RULE_CONFIG["weights"]

    numerator = sum(
        weights.get(name, 0.0) * value for name, value in values.items()
    )
    # The active target weights sum to 1.00; legacy aliases have 0.00 weight
    active_weight_sum = sum(
        weights.get(name, 0.0)
        for name in (
            "occasion_fit",
            "pairing_strength",
            "color_harmony",
            "style_coherence",
            "vibe_affinity",
            "formality_fit",
            "season_fit",
            "freshness",
            "style_dna",
            "layering",
        )
    )
    denominator = active_weight_sum if active_weight_sum > 0 else 1.0
    return round(max(0.0, min(1.0, numerator / denominator)), 3)
