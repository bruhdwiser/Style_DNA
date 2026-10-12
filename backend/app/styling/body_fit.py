"""Body-fit scoring based on shape preferences.

Ported from StyleSenseAI body/fit.py — the YAML-based rules are embedded
as Python dicts so the engine remains I/O-free. All guidance is neutral,
body-positive, and focused on silhouette balance.

Body shape is optional; when absent the score defaults to 0.5 (neutral).
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Embedded body-rules data (ported from body_rules.yaml)
# Only the preference weights are needed for scoring; the full silhouette
# recommendations live in the YAML and are surfaced by the explanation layer.
# ---------------------------------------------------------------------------

_BODY_RULES: dict[str, dict[str, dict[str, dict[str, dict[str, float]]]]] = {
    "manual": {
        "Hourglass": {
            "neckline": {"v_neck": 1.0, "scoop_neck": 0.9, "boat_neck": 0.7, "round_neck": 0.5},
            "fit": {"tailored": 1.0, "slim": 0.8, "regular": 0.6, "relaxed": 0.4},
            "length": {"midi": 0.8, "maxi": 0.7},
            "rise": {"high_rise": 0.9, "mid_rise": 0.7},
            "subcategory": {"dress": 0.9, "skirt": 0.8, "top": 0.7},
        },
        "Pear": {
            "neckline": {"boat_neck": 1.0, "scoop_neck": 0.9, "v_neck": 0.7, "collared": 0.5},
            "fit": {"regular": 1.0, "relaxed": 0.8, "tailored": 0.6, "slim": 0.4},
            "length": {"midi": 0.8, "maxi": 0.7},
            "rise": {"high_rise": 0.9, "mid_rise": 0.8},
            "subcategory": {"skirt": 0.9, "trousers": 0.8, "dress": 0.7},
        },
        "Inverted Triangle": {
            "neckline": {"v_neck": 1.0, "scoop_neck": 0.9, "round_neck": 0.5},
            "fit": {"relaxed": 1.0, "wide_leg": 0.9, "regular": 0.8, "tailored": 0.5},
            "length": {"maxi": 0.9, "midi": 0.8},
            "rise": {"mid_rise": 0.8, "low_rise": 0.5},
            "subcategory": {"trousers": 0.9, "dress": 0.8, "skirt": 0.8},
        },
        "Rectangle": {
            "neckline": {"boat_neck": 0.8, "scoop_neck": 0.7, "collared": 0.7},
            "fit": {"regular": 1.0, "tailored": 0.9, "slim": 0.7, "relaxed": 0.6},
            "length": {"midi": 0.9, "maxi": 0.7},
            "rise": {"high_rise": 0.9, "mid_rise": 0.8},
            "subcategory": {"dress": 0.9, "jacket": 0.8, "trousers": 0.7},
        },
        "Apple": {
            "neckline": {"v_neck": 1.0, "scoop_neck": 0.9, "mandarin_collar": 0.5},
            "fit": {"relaxed": 1.0, "regular": 0.8, "straight": 0.8, "slim": 0.4},
            "length": {"maxi": 0.9, "midi": 0.7},
            "rise": {"mid_rise": 0.8, "high_rise": 0.7},
            "subcategory": {"tunic": 0.9, "dress": 0.8, "trousers": 0.8},
        },
    },
}


def _normalize(value: Any) -> str:
    return str(value).strip().lower().replace(" ", "_")


def body_fit(
    attrs: dict[str, Any],
    shape: str,
    source: str = "manual",
) -> float:
    """Return a 0..1 fit score for *shape*, using embedded preference weights.

    Parameters
    ----------
    attrs:
        Garment attribute dict (keys like ``neckline``, ``fit``, ``length``,
        ``rise``, ``subcategory``).
    shape:
        Body-shape name (e.g. ``"Hourglass"``). Case-sensitive to match the
        embedded data; callers should title-case before calling.
    source:
        ``"manual"`` (default). Kept for forward-compatibility with a future
        photo-classification source.

    Returns
    -------
    float
        A value between 0.0 and 1.0.  Returns 0.5 (neutral) when *shape*
        is missing, unknown, or *attrs* is empty.
    """
    if not isinstance(attrs, dict) or not shape:
        return 0.5

    source_rules = _BODY_RULES.get(source, _BODY_RULES.get("manual", {}))
    preferences = source_rules.get(shape, {})
    if not preferences:
        return 0.5

    total_weight = 0.0
    weighted_score = 0.0

    for attribute_name, values in preferences.items():
        incoming_value = attrs.get(attribute_name)
        if incoming_value is None:
            continue
        normalized = _normalize(incoming_value)
        match_weight = values.get(normalized, 0.0)
        if match_weight <= 0:
            continue
        weighted_score += match_weight
        total_weight += 1.0

    if total_weight <= 0:
        return 0.5

    score = weighted_score / total_weight
    return round(max(0.0, min(1.0, score)), 3)
