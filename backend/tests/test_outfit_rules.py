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


def test_formality_spread_rule(make_item):
    """Verify that outfits with formality spread > 2 are rejected by check_formality_spread."""
    from app.styling.rules import check_formality_spread

    # Compatible: max diff <= 2
    pass_candidate = OutfitCandidate(
        slots={
            "top": make_item("top", "t1", formality=2),
            "bottom": make_item("bottom", "b1", formality=3),
            "shoes": make_item("shoes", "s1", formality=4),
        },
        skeleton="top_bottom",
    )
    assert check_formality_spread(pass_candidate) is True

    # Incompatible: formality 1 (lounge) with formality 4 (black tie) -> spread 3
    fail_candidate = OutfitCandidate(
        slots={
            "top": make_item("top", "t1", formality=1),
            "bottom": make_item("bottom", "b1", formality=4),
            "shoes": make_item("shoes", "s1", formality=2),
        },
        skeleton="top_bottom",
    )
    assert check_formality_spread(fail_candidate) is False
    assert hard_filter_candidate(fail_candidate, occasion="casual", season="all_season") is False


def test_pattern_clash_rule(make_item):
    """Verify that multiple loud patterns are rejected by check_pattern_clash."""
    from app.styling.rules import check_pattern_clash

    # One loud pattern with solid items -> passes
    single_loud = OutfitCandidate(
        slots={
            "top": make_item("top", "t1", pattern="floral"),
            "bottom": make_item("bottom", "b1", pattern="solid"),
            "shoes": make_item("shoes", "s1", pattern="solid"),
        },
        skeleton="top_bottom",
    )
    assert check_pattern_clash(single_loud) is True

    # Two loud patterns (e.g., animal print + chevron) -> fails
    two_loud = OutfitCandidate(
        slots={
            "top": make_item("top", "t1", pattern="animal_print"),
            "bottom": make_item("bottom", "b1", pattern="chevron"),
            "shoes": make_item("shoes", "s1", pattern="solid"),
        },
        skeleton="top_bottom",
    )
    assert check_pattern_clash(two_loud) is False
    assert hard_filter_candidate(two_loud, occasion="casual", season="all_season") is False


def test_pairing_graph_rule(make_item):
    """Verify pairing graph rejects forbidden edges like saree + sneakers/flip-flops."""
    from app.styling.rules import check_pairing_graph

    # Saree with formal shoes -> passes
    saree_sandals = OutfitCandidate(
        slots={
            "saree": make_item("saree", "sr1", formality=4),
            "shoes": make_item("shoes", "sh1", subcategory="sandals", formality=3),
        },
        skeleton="saree",
    )
    assert check_pairing_graph(saree_sandals) is True

    # Saree with sneakers -> fails
    saree_sneakers = OutfitCandidate(
        slots={
            "saree": make_item("saree", "sr1", formality=4),
            "shoes": make_item("shoes", "sh1", subcategory="sneakers", formality=1),
        },
        skeleton="saree",
    )
    assert check_pairing_graph(saree_sneakers) is False
    assert hard_filter_candidate(saree_sneakers, occasion="wedding", season="all_season") is False


def test_canonical_taxonomy_and_roles(make_item):
    """Verify canonical occasion mapping and PieceRole derivation."""
    from app.styling.taxonomy import canonical_occasion, derive_canonical_role, PieceRole

    assert canonical_occasion("office") == "work"
    assert canonical_occasion("Gym") == "gym"
    assert canonical_occasion("workout") == "gym"
    assert canonical_occasion("Night Out") == "party"
    assert canonical_occasion("haldi") == "festive"
    assert canonical_occasion("casual") == "casual"

    # Piece role checks
    assert derive_canonical_role("saree", "saree") == PieceRole.SAREE
    assert derive_canonical_role("outer", "blazer") == PieceRole.LAYER
    assert derive_canonical_role("shoes", "sneakers") == PieceRole.SHOES
    assert derive_canonical_role("top", "kurta") == PieceRole.TOP

