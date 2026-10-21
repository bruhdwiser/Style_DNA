"""Template-based outfit explanations grounded in rule component scores.

Ported from StyleSenseAI outfits/explain.py — deterministic, no I/O.
Produces factual, structured reasons (3–5 lines) that explain *why* the
engine chose an outfit, anchored in the feature scores.
"""

from __future__ import annotations

from typing import Any

from app.styling.features import feature_scores


def _coerce_item(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, item.get(key.replace("_", ""), default))
    return getattr(item, key, default)


def explain_outfit(
    candidate: Any,
    *,
    occasion: Any,
    season: Any,
    vibe: str | None = None,
    vibes: list[str] | None = None,
    body_shape: str | None = None,
    attrs: dict[str, Any] | None = None,
    affinities: dict[str, Any] | None = None,
) -> list[str]:
    """Return three to five factual reasons that explain the outfit score.

    Each reason references a specific feature dimension and its numeric value.
    The output is deterministic given the same candidate and context.
    """
    from app.styling.learning import compute_outfit_affinity_adjustment

    scores = feature_scores(
        candidate,
        occasion=occasion,
        season=season,
        vibe=vibe,
        vibes=vibes,
        body_shape=body_shape,
        attrs=attrs,
    )
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)

    reasons: list[str] = []

    # Check for explainable Style DNA affinity influence
    if affinities:
        _, dna_reasons = compute_outfit_affinity_adjustment(candidate, affinities)
        for r in dna_reasons:
            reasons.append(r)

    if isinstance(candidate, dict):
        slots = _coerce_item(candidate, "slots", {})
    else:
        slots = getattr(candidate, "slots", {})

    item_names: list[str] = []
    for item in slots.values():
        item_name = _coerce_item(
            item, "name", _coerce_item(item, "category", "item")
        )
        if item_name not in (None, ""):
            item_names.append(str(item_name))

    has_target_vibe = bool((vibe and str(vibe).strip()) or (vibes and any(str(v).strip() for v in vibes)))
    target_vibe_label = (
        str(vibe).strip().lower()
        if vibe and str(vibe).strip()
        else (str(vibes[0]).strip().lower() if vibes and vibes[0] else None)
    )

    # Filter out body_fit and legacy duplicates; exclude vibe_affinity when no vibe was requested
    excluded_names = {"body_fit", "color", "style", "occasion", "season", "novelty"}
    if not has_target_vibe:
        excluded_names.add("vibe_affinity")

    filtered_scores = [
        (name, value) for name, value in ordered
        if name not in excluded_names
    ]
    if has_target_vibe and "vibe_affinity" in scores:
        vibe_val = scores["vibe_affinity"]
        other_scores = [item for item in filtered_scores if item[0] != "vibe_affinity"]
        explanation_scores = [("vibe_affinity", vibe_val)] + other_scores
    else:
        explanation_scores = filtered_scores if filtered_scores else ordered

    if explanation_scores:
        for name, value in explanation_scores[:4]:
            label = name.replace("_", " ").title()
            if name == "body_fit":
                continue  # Decoupled from outfit explanations
            elif name in ("color_harmony", "color"):
                colors = [
                    str(_coerce_item(item, "color", "item"))
                    for item in slots.values()
                    if _coerce_item(item, "color", None) is not None
                ]
                colors_text = ", ".join(colors) if colors else "used colors"
                if value >= 0.90:
                    reasons.append(
                        f"Color harmony is {value:.2f} with a cohesive, polished palette "
                        f"({colors_text})."
                    )
                else:
                    reasons.append(
                        f"Color harmony is {value:.2f} across the palette "
                        f"({colors_text})."
                    )
            elif name in ("occasion_fit", "occasion"):
                reasons.append(
                    f"Occasion fit is {value:.2f} meeting the dress code for {occasion}."
                )
            elif name in ("season_fit", "season"):
                reasons.append(
                    f"Season fit is {value:.2f} for {season} styling."
                )
            elif name == "pairing_strength":
                skel_name = getattr(candidate, "skeleton", "outfit").replace("_", " ")
                reasons.append(
                    f"Pairing strength is {value:.2f} across compatible {skel_name} pieces."
                )
            elif name in ("style_coherence", "style"):
                reasons.append(
                    f"Style coherence is {value:.2f} aligning pieces within the aesthetic."
                )
            elif name == "vibe_affinity":
                if target_vibe_label:
                    if value >= 0.70:
                        reasons.append(
                            f"Strong {target_vibe_label} match ({value:.2f}) aligning with your requested aesthetic."
                        )
                    elif value >= 0.35:
                        reasons.append(
                            f"Moderate {target_vibe_label} affinity ({value:.2f}) balancing {occasion} styling."
                        )
                    else:
                        reasons.append(
                            f"Wardrobe has limited {target_vibe_label} options for {occasion}; prioritized occasion fit and structural pairing."
                        )
                else:
                    reasons.append(
                        f"Vibe affinity is {value:.2f} matching the desired aesthetic."
                    )
            elif name == "formality_fit":
                reasons.append(
                    f"Formality fit is {value:.2f} within a balanced dress code spread."
                )
            elif name == "layering":
                reasons.append(
                    f"Layering adds {value:.2f} polish through the selected layer piece."
                )
            elif name in ("freshness", "novelty"):
                reasons.append(
                    f"Freshness is {value:.2f}, keeping the look distinct and contemporary."
                )
            else:
                reasons.append(
                    f"{label} contributes {value:.2f} to the overall recommendation."
                )

    # Pad to at least 3 reasons
    if len(reasons) < 3:
        reasons.extend([
            (
                f"The outfit uses {len(slots)} slots across "
                f"{', '.join(item_names[:3]) if item_names else 'selected pieces'}."
            ),
            f"The look is set for {occasion} and {season} conditions.",
            "The skeleton remains structurally valid and season-compatible.",
        ])

    # Deduplicate while preserving order
    deduped: list[str] = []
    for reason in reasons:
        if reason not in deduped:
            deduped.append(reason)
    return deduped[:5]
