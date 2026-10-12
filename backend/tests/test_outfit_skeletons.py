"""Tests for outfit skeletons, slot matching, and candidate generation."""

from app.styling.skeletons import generate_candidates


def test_generates_western_top_bottom_combinations(make_item):
    """Verify standard top + bottom + shoes skeleton combinations."""
    items = [
        make_item("top", "t1"),
        make_item("bottom", "b1"),
        make_item("shoes", "s1"),
    ]
    candidates = generate_candidates(items)
    assert len(candidates) >= 1
    assert any(c.skeleton == "top_bottom" for c in candidates)
    c = next(c for c in candidates if c.skeleton == "top_bottom")
    assert "top" in c.slots
    assert "bottom" in c.slots
    assert "shoes" in c.slots


def test_generates_saree_skeleton(make_item):
    """Verify that saree is recognized as a complete 1-piece look with shoes."""
    items = [
        make_item("saree", "sr1"),
        make_item("shoes", "s1"),
    ]
    candidates = generate_candidates(items)
    assert any(c.skeleton == "saree" for c in candidates)
    c = next(c for c in candidates if c.skeleton == "saree")
    assert "saree" in c.slots
    assert "shoes" in c.slots


def test_generates_dress_skeleton(make_item):
    """Verify dress + shoes skeleton generation."""
    items = [
        make_item("dress", "d1"),
        make_item("shoes", "s1"),
    ]
    candidates = generate_candidates(items)
    assert any(c.skeleton == "dress" for c in candidates)


def test_candidate_generation_is_bounded_and_does_not_explode(make_item):
    """Verify candidate generation caps at max_candidates to protect performance."""
    # 20 tops, 20 bottoms, 20 shoes = 8,000 Cartesian product
    tops = [make_item("top", f"t{i}") for i in range(20)]
    bottoms = [make_item("bottom", f"b{i}") for i in range(20)]
    shoes = [make_item("shoes", f"s{i}") for i in range(20)]

    candidates = generate_candidates(tops + bottoms + shoes, max_candidates=500)
    assert len(candidates) <= 500
