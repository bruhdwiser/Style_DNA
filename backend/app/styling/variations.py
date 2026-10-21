"""Variant plans for outfit adjustments using constraint and weight nudges.

Ported from StyleSenseAI outfits/variations.py — pure Python, no I/O.

Each variation type adjusts the constraint set and scoring weights so the
generator can re-rank or re-filter candidates to produce stylistically
different results from the same wardrobe.
"""

from __future__ import annotations

from typing import Any


VARIATION_TYPES: tuple[str, ...] = (
    "more_casual",
    "more_formal",
    "more_layered",
    "monochrome",
    "weekend_relaxed",
    "work_ready",
    "bold_statement",
    "seasonal_refresh",
)


def _normalize(value: Any) -> str:
    return str(value).strip().lower().replace(" ", "_")


from app.styling.rules import OUTFIT_RULE_CONFIG


def _base_plan(variation_type: str) -> dict[str, Any]:
    """Create a variation plan with default weights."""
    return {
        "type": variation_type,
        "constraints": {},
        "weights": dict(OUTFIT_RULE_CONFIG["weights"]),
    }


def generate_variations(
    candidate: Any,
    *,
    occasion: Any = "casual",
    season: Any = "all_season",
    variation_type: str | None = None,
) -> list[dict[str, Any]]:
    """Return a deterministic set of variation plans built from the candidate.

    Each plan includes adjusted weights and constraints that the generator
    can use to produce a variant of the original outfit.  If *variation_type*
    is specified, only matching plans are returned.
    """
    if isinstance(candidate, dict):
        slots = candidate.get("slots", candidate)
    else:
        slots = getattr(candidate, "slots", {})

    plans: list[dict[str, Any]] = []
    for variation in VARIATION_TYPES:
        plan = _base_plan(variation)
        key = _normalize(variation)

        if key == "more_casual":
            plan["constraints"] = {"occasion_max_formality": 1}
            plan["weights"] = {
                **plan["weights"],
                "occasion": 0.22,
                "style": 0.22,
                "novelty": 0.04,
            }
        elif key == "more_formal":
            plan["constraints"] = {"occasion_min_formality": 2}
            plan["weights"] = {
                **plan["weights"],
                "occasion": 0.22,
                "style": 0.18,
                "color": 0.16,
            }
        elif key == "more_layered":
            plan["constraints"] = {"require_layer": True}
            plan["weights"] = {
                **plan["weights"],
                "layering": 0.18,
                "style": 0.18,
            }
        elif key == "monochrome":
            plan["constraints"] = {"color_similarity": 0.7}
            plan["weights"] = {
                **plan["weights"],
                "color": 0.32,
                "style": 0.12,
            }
        elif key == "weekend_relaxed":
            plan["constraints"] = {
                "occasion_max_formality": 1,
                "relaxed_fit": True,
            }
            plan["weights"] = {
                **plan["weights"],
                "style": 0.20,
                "novelty": 0.08,
                "occasion": 0.18,
            }
        elif key == "work_ready":
            plan["constraints"] = {"occasion": "work", "season": season}
            plan["weights"] = {
                **plan["weights"],
                "occasion": 0.28,
                "body_fit": 0.28,
                "style": 0.18,
            }
        elif key == "bold_statement":
            plan["constraints"] = {"novelty_min": 0.6}
            plan["weights"] = {
                **plan["weights"],
                "novelty": 0.18,
                "color": 0.24,
                "style": 0.20,
            }
        elif key == "seasonal_refresh":
            plan["constraints"] = {"season": season}
            plan["weights"] = {
                **plan["weights"],
                "season": 0.20,
                "color": 0.18,
                "layering": 0.08,
            }

        plan["candidate"] = slots
        plans.append(plan)

    if variation_type is not None:
        requested = _normalize(variation_type)
        filtered = [plan for plan in plans if plan["type"] == requested]
        if filtered:
            return filtered

    return plans
