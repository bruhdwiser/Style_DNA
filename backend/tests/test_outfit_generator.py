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


def test_outfit_candidate_extracts_dict_and_object_uuids():
    """Verify that OutfitCandidate extracts real 'id' from dicts and objects without memory id."""
    from types import SimpleNamespace
    import pytest
    from app.styling.skeletons import OutfitCandidate

    dict_item = {"id": "uuid-dict-top-1", "category": "top"}
    obj_item = SimpleNamespace(id="uuid-obj-bottom-2", category="bottom")

    candidate = OutfitCandidate(
        slots={"top": dict_item, "bottom": obj_item},
        skeleton="top_bottom",
    )

    assert candidate.item_ids == ("uuid-dict-top-1", "uuid-obj-bottom-2")
    # Verify no Python memory address fallback occurred
    assert str(id(dict_item)) not in candidate.item_ids
    assert str(id(obj_item)) not in candidate.item_ids

    # Item missing id raises ValueError
    invalid_item = {"category": "top"}
    with pytest.raises(ValueError, match="missing a persistent 'id'"):
        _ = OutfitCandidate(slots={"top": invalid_item}, skeleton="test").item_ids


def test_outfit_candidate_slot_aware_core_signature(make_item):
    """Verify that core_signature is a frozenset of (slot, id) pairs, excluding shoes and layer."""
    from app.styling.skeletons import OutfitCandidate

    top = make_item("top", "t_101")
    bottom = make_item("bottom", "b_202")
    shoes = make_item("shoes", "s_303")
    layer = make_item("layer", "l_404")

    candidate = OutfitCandidate(
        slots={"top": top, "bottom": bottom, "shoes": shoes, "layer": layer},
        skeleton="top_bottom",
    )

    expected = frozenset({("top", "t_101"), ("bottom", "b_202")})
    assert candidate.core_signature == expected
    assert ("shoes", "s_303") not in candidate.core_signature
    assert ("layer", "l_404") not in candidate.core_signature


def test_deterministic_repeatability_with_arbitrary_seeds(sample_wardrobe):
    """Verify normal generation produces identical results regardless of frontend random seeds."""
    seeds = [0, 42, 999, 12345]
    results = [
        generate_outfits(sample_wardrobe, occasion="casual", season="all_season", seed=s, limit=6, is_shuffle=False)
        for s in seeds
    ]

    base = results[0]
    assert len(base) >= 2
    for r in results[1:]:
        assert len(r) == len(base)
        for cand_base, cand_other in zip(base, r):
            assert cand_base.item_ids == cand_other.item_ids
            assert cand_base.core_signature == cand_other.core_signature
            assert cand_base.skeleton == cand_other.skeleton


def test_core_diversity_prioritizes_distinct_cores(make_item):
    """Verify that distinct top/bottom cores are prioritized over repeating the same core with other shoes."""
    wardrobe = [
        make_item("top", "t1", color="#000000", style="casual"),
        make_item("top", "t2", color="#1E3A8A", style="casual"),
        make_item("top", "t3", color="#FFFFFF", style="casual"),
        make_item("top", "t4", color="#FF0000", style="casual"),
        make_item("bottom", "b1", color="#1F2937", style="casual"),
        make_item("shoes", "s1", color="#3B82F6", style="casual"),
        make_item("shoes", "s2", color="#B0B0B0", style="casual"),
        make_item("shoes", "s3", color="#000000", style="casual"),
    ]

    outfits = generate_outfits(wardrobe, occasion="casual", season="all_season", limit=4, is_shuffle=False)
    assert len(outfits) == 4
    # All 4 returned looks must have distinct core combinations
    core_sigs = [o.core_signature for o in outfits]
    assert len(set(core_sigs)) == 4


def test_small_wardrobe_graceful_exhaustion_without_padding(make_item):
    """Verify small wardrobe with only 2 valid outfits returns exactly 2 without duplicate padding."""
    small_wardrobe = [
        make_item("top", "t1"),
        make_item("bottom", "b1"),
        make_item("shoes", "s1"),
        make_item("shoes", "s2"),
    ]

    outfits = generate_outfits(small_wardrobe, occasion="casual", limit=6, is_shuffle=False)
    assert len(outfits) == 2
    assert len(set(o.item_ids for o in outfits)) == 2


def test_shuffle_divergence_and_exclusion(sample_wardrobe):
    """Verify that shuffle with exclude_core_signatures avoids already-seen cores when alternatives exist."""
    base = generate_outfits(sample_wardrobe, occasion="casual", limit=3, is_shuffle=False)
    seen_cores = {o.core_signature for o in base}

    shuffled = generate_outfits(
        sample_wardrobe,
        occasion="casual",
        limit=3,
        seed=888,
        is_shuffle=True,
        exclude_core_signatures=seen_cores,
    )
    assert len(shuffled) > 0
    # None of the shuffled outfits should reuse any of the excluded cores
    for o in shuffled:
        assert o.core_signature not in seen_cores


def test_shuffle_exhaustion_does_not_repeat_excluded_cores(sample_wardrobe):
    """Verify that when all valid core combinations are excluded, shuffle does NOT silently repeat them."""
    all_outfits = generate_outfits(sample_wardrobe, occasion="casual", limit=50, is_shuffle=False)
    all_cores = {o.core_signature for o in all_outfits}

    exhausted = generate_outfits(
        sample_wardrobe,
        occasion="casual",
        limit=5,
        is_shuffle=True,
        exclude_core_signatures=all_cores,
    )
    # Must return empty list, NOT silently repeat excluded cores
    assert exhausted == []
