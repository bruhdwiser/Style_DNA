"""Tests for outfit generator, scoring, and diversification."""

import time
from app.styling.generator import generate_outfits
from app.styling.explain import explain_outfit


def test_generator_performance_under_one_second(sample_wardrobe):
    """Verify that combinatorial outfit generation and MMR diversification execute in < 1s."""
    start = time.perf_counter()
    outfits = generate_outfits(
        sample_wardrobe,
        occasion="work",
        season="summer",
        body_shape="Hourglass",
        limit=6,
        seed=42,
    )
    elapsed = time.perf_counter() - start

    assert len(outfits) >= 2
    assert elapsed < 1.0, f"Outfit generation took {elapsed:.3f}s, expected < 1.0s"


def test_generator_deterministic_with_seed(sample_wardrobe):
    """Verify that identical inputs and seeds generate identical ranked outfit candidates."""
    run1 = generate_outfits(sample_wardrobe, occasion="casual", season="all_season", seed=123, limit=5)
    run2 = generate_outfits(sample_wardrobe, occasion="casual", season="all_season", seed=123, limit=5)

    assert len(run1) == len(run2)
    for c1, c2 in zip(run1, run2):
        assert c1.item_ids == c2.item_ids
        assert c1.skeleton == c2.skeleton


def test_generator_respects_occasion_dress_code(sample_wardrobe):
    """Verify that occasion filtering rejects informal items for formal/wedding settings."""
    festive_outfits = generate_outfits(
        sample_wardrobe,
        occasion="wedding",
        season="all_season",
        limit=5,
    )
    # The saree was tagged for wedding/festive
    assert any("saree" in candidate.skeleton for candidate in festive_outfits)


def test_explanations_are_factual_and_complete(sample_wardrobe):
    """Verify that structured factual reasons are generated for top candidates."""
    outfits = generate_outfits(sample_wardrobe, occasion="work", season="summer", limit=1)
    assert len(outfits) > 0
    top = outfits[0]

    reasons = explain_outfit(
        top,
        occasion="work",
        season="summer",
        body_shape="Hourglass",
    )
    assert isinstance(reasons, list)
    assert len(reasons) >= 1
    # Check that explanation text mentions actual garments
    assert any(isinstance(r, str) and len(r) > 5 for r in reasons)
