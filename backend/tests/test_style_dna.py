"""Tests for Style DNA feedback events, transparent learning, and bounded ranking influence."""

from app.styling.learning import (
    calculate_affinities,
    compute_outfit_affinity_adjustment,
    MAX_AFFINITY_INFLUENCE,
)
from app.styling.skeletons import OutfitCandidate


def test_wear_and_like_increase_positive_affinities(make_item):
    """Verify that wear (+3) and like (+1) events raise color and style affinities."""
    events = [
        {
            "event_type": "wear",
            "metadata": {
                "colors": ["#1E3A8A"],
                "styles": ["tailored"],
                "categories": ["top", "bottom"],
            },
        },
        {
            "event_type": "like",
            "metadata": {
                "colors": ["#1E3A8A"],
                "styles": ["casual"],
                "categories": ["top"],
            },
        },
    ]

    result = calculate_affinities(events)

    # #1E3A8A should have high positive affinity (> 0.5 neutral)
    color_affinities = result["affinities"]["colors"]
    assert "#1E3A8A".lower() in color_affinities
    assert color_affinities["#1E3A8A".lower()] > 0.65


def test_dislike_lowers_affinity(make_item):
    """Verify that dislike events push affinities below 0.5."""
    events = [
        {
            "event_type": "dislike",
            "metadata": {
                "colors": ["#FF0000"],
                "styles": ["neon"],
                "categories": ["top"],
            },
        },
        {
            "event_type": "dislike",
            "metadata": {
                "colors": ["#FF0000"],
                "styles": ["neon"],
                "categories": ["top"],
            },
        },
    ]

    result = calculate_affinities(events)
    color_affinities = result["affinities"]["colors"]
    assert color_affinities["#FF0000".lower()] < 0.4


def test_affinity_influence_is_strictly_bounded(make_item):
    """Verify that Style DNA influence never exceeds MAX_AFFINITY_INFLUENCE (0.08)."""
    # Extremely polarized affinities
    extreme_affinities = {
        "total_events": 10,
        "affinities": {
            "colors": {"#000000": 1.0, "#ffffff": 0.0},
            "styles": {"tailored": 1.0, "grunge": 0.0},
            "categories": {"top": 1.0, "shoes": 1.0},
        },
    }

    candidate = OutfitCandidate(
        slots={
            "top": make_item("top", "t1", color="#000000", style="tailored"),
            "bottom": make_item("bottom", "b1", color="#000000", style="tailored"),
            "shoes": make_item("shoes", "s1", color="#000000", style="tailored"),
        },
        skeleton="top_bottom",
    )

    delta, reasons = compute_outfit_affinity_adjustment(candidate, extreme_affinities)
    assert isinstance(delta, float)
    assert abs(delta) <= MAX_AFFINITY_INFLUENCE + 1e-6
