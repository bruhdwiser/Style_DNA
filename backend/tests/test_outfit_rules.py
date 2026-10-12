"""Tests for deterministic outfit rules, formality, and hard filters."""

from app.styling.rules import (
    hard_filter_candidate,
    no_two_bottoms,
    no_formal_shoes_for_lounge,
)
from app.styling.skeletons import OutfitCandidate


def test_no_two_bottoms_rejected(make_item):
    """Verify that outfits containing multiple conflicting bottoms are rejected."""
    candidate = OutfitCandidate(
        slots={
            "top": make_item("top", "t1"),
            "bottom": make_item("bottom", "b1"),
            "ethnic_bottom": make_item("ethnic_bottom", "eb1"),
            "shoes": make_item("shoes", "s1"),
        },
        skeleton="top_bottom",
    )
    assert no_two_bottoms(candidate) is False
    assert hard_filter_candidate(candidate, occasion="casual", season="all_season") is False


def test_formal_shoes_rejected_for_lounge(make_item):
    """Verify that formal shoes are strictly rejected for relaxing/lounge occasions."""
    candidate = OutfitCandidate(
        slots={
            "top": make_item("top", "t1", formality=1),
            "bottom": make_item("bottom", "b1", formality=1),
            "shoes": make_item("shoes", "s1", formality=3, style="formal"),
        },
        skeleton="top_bottom",
    )
    assert no_formal_shoes_for_lounge(candidate, occasion="lounge") is False
    assert hard_filter_candidate(candidate, occasion="lounge", season="all_season") is False


def test_season_compatibility_filter(make_item):
    """Verify that winter-only garments are not suggested for extreme summer."""
    candidate = OutfitCandidate(
        slots={
            "top": make_item("top", "t1", seasons=["winter"], season="winter"),
            "bottom": make_item("bottom", "b1", seasons=["all_season"]),
            "shoes": make_item("shoes", "s1", seasons=["all_season"]),
        },
        skeleton="top_bottom",
    )
    assert hard_filter_candidate(candidate, occasion="casual", season="summer") is False
