"""Tests for counterfactual wardrobe gap analysis and catalog suggestion logic."""

from app.styling.gaps import analyze_gaps, rank_gaps, load_archetypes


def test_gap_analysis_unlocks_outfits_when_slot_missing(make_item):
    """Verify that a wardrobe missing bottoms identifies bottoms as a high-utility gap."""
    # Wardrobe with tops and shoes, but 0 bottoms
    incomplete_wardrobe = [
        make_item("top", "t1", style="casual", color="#000000"),
        make_item("top", "t2", style="casual", color="#FFFFFF"),
        make_item("shoes", "s1", style="casual", color="#111827"),
    ]

    gaps_result = analyze_gaps(incomplete_wardrobe, occasions=["casual", "college"])
    results = gaps_result["results"]

    assert len(results) > 0
    # Bottom archetypes should unlock positive new outfits
    bottom_gaps = [g for g in results if g["category"] == "bottom"]
    assert len(bottom_gaps) > 0
    top_bottom_gap = bottom_gaps[0]
    assert top_bottom_gap["new_outfits_total"] >= 2
    assert top_bottom_gap["utility"] > 0


def test_gap_analysis_is_deterministic(sample_wardrobe):
    """Verify that multiple gap runs produce identical rankings and utilities."""
    first = rank_gaps(sample_wardrobe, occasions=["work", "casual"])
    second = rank_gaps(sample_wardrobe, occasions=["work", "casual"])

    assert len(first) == len(second)
    for g1, g2 in zip(first, second):
        assert g1["id"] == g2["id"]
        assert g1["utility"] == g2["utility"]
        assert g1["new_outfits_total"] == g2["new_outfits_total"]


def test_load_archetypes_contains_women_and_unisex_staples():
    """Verify default archetypes contain classic staples."""
    archetypes = load_archetypes()
    assert len(archetypes) >= 4
    categories = {a["category"] for a in archetypes}
    assert "bottom" in categories
    assert "shoes" in categories
    assert "top" in categories
