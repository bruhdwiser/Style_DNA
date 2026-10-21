"""Counterfactual gap analysis for outfit archetypes and virtual items.

Ported from StyleSenseAI apps/api/app/services/catalog/gaps.py — pure Python,
no YAML/file I/O, deterministic calculation of unlocked wardrobe outfits.
"""

from __future__ import annotations

from typing import Any

from app.styling.generator import generate_outfits
from app.styling.rules import MIN_OUTFIT_SCORE_GAP_ANALYSIS

DEFAULT_ARCHETYPES: list[dict[str, Any]] = [
    {
        "id": "beige_linen_trousers",
        "name": "Beige linen trousers",
        "category": "bottom",
        "style": "relaxed",
        "color": "#E5E7EB",
        "suitability": 0.9,
        "occasions": ["college", "work"],
        "virtual_item": {
            "id": "virtual_beige_linen_trousers",
            "category": "bottom",
            "style": "relaxed",
            "color": "#E5E7EB",
            "formality": 1,
            "season": "summer",
            "seasons": ["summer", "all_season"],
            "occasions": ["college", "work"],
            "is_available": True,
        },
    },
    {
        "id": "white_sneakers",
        "name": "White sneakers",
        "category": "shoes",
        "style": "casual",
        "color": "#FFFFFF",
        "suitability": 0.7,
        "occasions": ["casual", "college"],
        "virtual_item": {
            "id": "virtual_white_sneakers",
            "category": "shoes",
            "style": "casual",
            "color": "#FFFFFF",
            "formality": 1,
            "season": "all_season",
            "seasons": ["all_season"],
            "occasions": ["casual", "college"],
            "is_available": True,
        },
    },
    {
        "id": "black_kurta",
        "name": "Black kurta",
        "category": "top",
        "style": "minimal",
        "color": "#111827",
        "suitability": 0.8,
        "occasions": ["festive", "work"],
        "virtual_item": {
            "id": "virtual_black_kurta",
            "category": "top",
            "style": "minimal",
            "color": "#111827",
            "formality": 2,
            "season": "all_season",
            "seasons": ["all_season"],
            "occasions": ["festive", "work"],
            "is_available": True,
        },
    },
    {
        "id": "silk_saree",
        "name": "Classic silk saree",
        "category": "saree",
        "style": "traditional",
        "color": "#831843",
        "suitability": 0.9,
        "occasions": ["wedding", "festive"],
        "virtual_item": {
            "id": "virtual_silk_saree",
            "category": "saree",
            "style": "traditional",
            "color": "#831843",
            "formality": 3,
            "season": "all_season",
            "seasons": ["all_season"],
            "occasions": ["wedding", "festive"],
            "is_available": True,
        },
    },
    {
        "id": "gold_jewelry",
        "name": "Statement gold jhumkas",
        "category": "jewelry",
        "style": "traditional",
        "color": "#F59E0B",
        "suitability": 0.8,
        "occasions": ["wedding", "festive", "party"],
        "virtual_item": {
            "id": "virtual_gold_jewelry",
            "category": "jewelry",
            "style": "traditional",
            "color": "#F59E0B",
            "formality": 3,
            "season": "all_season",
            "seasons": ["all_season"],
            "occasions": ["wedding", "festive", "party"],
            "is_available": True,
        },
    },
    {
        "id": "tan_tote_bag",
        "name": "Structured tan tote",
        "category": "bag",
        "style": "classic",
        "color": "#B45309",
        "suitability": 0.75,
        "occasions": ["work", "college", "casual"],
        "virtual_item": {
            "id": "virtual_tan_tote_bag",
            "category": "bag",
            "style": "classic",
            "color": "#B45309",
            "formality": 2,
            "season": "all_season",
            "seasons": ["all_season"],
            "occasions": ["work", "college", "casual"],
            "is_available": True,
        },
    },
]


def load_archetypes() -> list[dict[str, Any]]:
    """Return the built-in deterministic archetypes with women-focused additions."""
    return [dict(archetype) for archetype in DEFAULT_ARCHETYPES]


def _normalize_occasion(value: Any) -> str:
    return str(value).strip().lower().replace(" ", "_")


def _virtual_item_for(archetype: dict[str, Any]) -> dict[str, Any]:
    virtual = dict(archetype.get("virtual_item") or {})
    if not virtual:
        virtual = {
            "id": archetype.get("id", "virtual_item"),
            "category": archetype.get("category", "top"),
            "style": archetype.get("style", "casual"),
            "color": archetype.get("color", "#FFFFFF"),
            "formality": 1,
            "season": "all_season",
            "seasons": ["all_season"],
            "occasions": archetype.get("occasions", []),
            "is_available": True,
        }
    virtual.setdefault("id", f"virtual_{archetype.get('id', 'item')}")
    virtual.setdefault("category", archetype.get("category", "top"))
    virtual.setdefault("is_available", True)
    return virtual


def _candidate_outfit_counts(items: list[Any], occasions: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for occasion in occasions:
        counts[occasion] = len(
            generate_outfits(items, occasion=occasion, season="all_season", seed=0, limit=1000)
        )
    return counts


def gap_for_archetype(
    archetype: dict[str, Any],
    wardrobe: list[Any],
    occasions: list[str] | None = None,
) -> dict[str, Any]:
    """Calculate the incremental outfit utility unlocked by a single archetype."""
    occasions = [
        _normalize_occasion(val)
        for val in (occasions or ["casual", "college", "work", "party", "formal", "festive", "wedding", "lounge"])
    ]
    unique_occasions = list(dict.fromkeys(occasions))
    suitability = float(archetype.get("suitability", 0.5) or 0.5)
    base_counts = _candidate_outfit_counts(wardrobe, unique_occasions)
    virtual_item = _virtual_item_for(archetype)
    simulated_wardrobe = [*wardrobe, virtual_item]
    simulated_counts = _candidate_outfit_counts(simulated_wardrobe, unique_occasions)

    new_outfits_by_occasion = {
        occasion: max(0, simulated_counts.get(occasion, 0) - base_counts.get(occasion, 0))
        for occasion in unique_occasions
    }
    total_new_outfits = sum(new_outfits_by_occasion.values())
    utility = round(float(total_new_outfits) * suitability, 3)
    return {
        "id": str(archetype.get("id", "virtual_item")),
        "name": str(archetype.get("name", "Virtual archetype")),
        "category": str(archetype.get("category", "top")),
        "suitability": round(suitability, 3),
        "new_outfits_total": total_new_outfits,
        "new_outfits_by_occasion": new_outfits_by_occasion,
        "utility": utility,
        "virtual_item": virtual_item,
    }


def rank_gaps(
    wardrobe: list[Any],
    occasions: list[str] | None = None,
    archetypes: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Rank all gap archetypes deterministically by utility descending."""
    pool = archetypes or load_archetypes()
    results = [gap_for_archetype(archetype, wardrobe, occasions) for archetype in pool]
    return sorted(
        results,
        key=lambda item: (-float(item["utility"]), -int(item["new_outfits_total"]), str(item["name"])),
    )


def analyze_gaps(
    wardrobe: list[Any],
    occasions: list[str] | None = None,
    archetypes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return top ranked gaps and summary count."""
    ranked = rank_gaps(wardrobe, occasions, archetypes)
    return {"results": ranked, "count": len(ranked)}
