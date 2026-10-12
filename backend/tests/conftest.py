"""Shared pytest fixtures for Flashfits AI styling engine tests.
"""

import os
import sys
from typing import Any
import pytest

# Ensure backend root is on sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)


@pytest.fixture
def make_item():
    """Factory fixture to create typed wardrobe item dicts for styling tests."""
    def _create(category: str, item_id: str, **kwargs: Any) -> dict[str, Any]:
        payload = {
            "id": item_id,
            "category": category,
            "is_available": True,
            "season": "all_season",
            "seasons": ["all_season"],
            "occasions": ["casual", "work", "college"],
            "color": "#000000",
            "style": "casual",
            "formality": 1,
            **kwargs,
        }
        return payload
    return _create


@pytest.fixture
def sample_wardrobe(make_item):
    """Rich capsule wardrobe fixture containing Western and Ethnic garments."""
    return [
        make_item("top", "t1", color="#000000", style="tailored", formality=2, neckline="v_neck"),
        make_item("top", "t2", color="#1E3A8A", style="casual", formality=1, neckline="round_neck"),
        make_item("top", "t3", color="#FFFFFF", style="classic", formality=1, neckline="boat_neck"),
        make_item("bottom", "b1", color="#FFFFFF", style="classic", formality=1, fit="straight"),
        make_item("bottom", "b2", color="#1F2937", style="tailored", formality=2, fit="tapered"),
        make_item("shoes", "s1", color="#B0B0B0", style="formal", formality=2),
        make_item("shoes", "s2", color="#3B82F6", style="casual", formality=1),
        make_item("layer", "l1", color="#F5F5DC", style="structured", formality=2),
        make_item("dress", "d1", color="#FF0000", style="dramatic", formality=3),
        make_item("saree", "sr1", color="#D97706", style="festive", formality=3, occasions=["wedding", "festive"]),
        make_item("ethnic_bottom", "eb1", color="#F3F4F6", style="traditional", formality=2),
    ]
