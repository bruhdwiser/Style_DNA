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

    if ordered:
        for name, value in ordered[:3]:
            label = name.replace("_", " ").title()
            if name == "body_fit":
                reasons.append(
                    f"Body-fit scoring is {value:.2f} for the "
                    f"{body_shape or 'current'} silhouette profile."
                )
            elif name == "color":
                colors = [
                    str(_coerce_item(item, "color", "item"))
                    for item in slots.values()
                    if _coerce_item(item, "color", None) is not None
                ]
                colors_text = ", ".join(colors) if colors else "used colors"
                reasons.append(
                    f"Color harmony is {value:.2f} across the palette "
                    f"({colors_text})."
                )
            elif name == "occasion":
                reasons.append(
                    f"Occasion fit is {value:.2f} for the {occasion} brief."
                )
            elif name == "season":
                reasons.append(
                    f"Season fit is {value:.2f} for {season} styling."
                )
            elif name == "layering":
                reasons.append(
                    f"Layering adds {value:.2f} polish through the selected "
                    f"layer pieces."
                )
            elif name == "novelty":
                reasons.append(
                    f"Novelty is {value:.2f}, which keeps the outfit "
                    f"contemporary without breaking the dress code."
                )
            else:
                reasons.append(
                    f"{label} contributes {value:.2f} to the overall "
                    f"recommendation."
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
