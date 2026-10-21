"""Deterministic wardrobe outfit skeletons and bounded candidate generation.

Ported from StyleSenseAI outfits/skeletons.py — pure Python, no I/O.

Women-focused defaults:
- ``saree`` is treated as a one-piece garment (like ``ethnic_set``).
- ``dupatta`` is an optional accessory for ethnic looks.
- ``jewelry`` is an optional slot for saree outfits.
- Kurta-like items classified as ``top`` combine with ``ethnic_bottom``.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from itertools import product
from typing import Any


def _value(item: Any, key: str, default: Any = None) -> Any:
    """Attribute accessor that handles both dicts and objects."""
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _extract_item_id(item: Any) -> str:
    """Extract persistent garment UUID without ever falling back to memory address."""
    val = _value(item, "id", None)
    if val is None or not str(val).strip():
        raise ValueError(f"Garment item {item!r} is missing a persistent 'id' attribute.")
    return str(val).strip()


CORE_SLOTS: frozenset[str] = frozenset({
    "top",
    "bottom",
    "ethnic_bottom",
    "dress",
    "ethnic_set",
    "saree",
})


@dataclass(frozen=True)
class OutfitCandidate:
    """A slot-to-item mapping and the skeleton used to create it."""

    slots: dict[str, Any]
    skeleton: str

    @property
    def item_ids(self) -> tuple[str, ...]:
        """Stable identity tuple used for deduplication and diversification."""
        return tuple(_extract_item_id(item) for item in self.slots.values())

    @property
    def core_signature(self) -> frozenset[tuple[str, str]]:
        """Stable set of (slot, garment_id) pairs for all core slots present."""
        return frozenset(
            (slot, _extract_item_id(item))
            for slot, item in self.slots.items()
            if slot in CORE_SLOTS
        )


# -----------------------------------------------------------------------
# Skeleton definitions
# -----------------------------------------------------------------------
# Each skeleton is a tuple of (name, required_slot_categories).
# Categories use normalised garment taxonomy names.

_SKELETONS: tuple[tuple[str, tuple[tuple[str, ...], ...]], ...] = (
    ("top_bottom", (("top",), ("bottom", "ethnic_bottom"), ("shoes",))),
    ("dress", (("dress",), ("shoes",))),
    ("ethnic_set", (("ethnic_set",), ("shoes",))),
    ("saree", (("saree",), ("shoes",))),
)

# Optional single-item additions — kept as separate candidates, not
# a Cartesian product, to prevent combinatorial explosion.
_OPTIONAL_CATEGORIES: dict[str, tuple[str, ...]] = {
    "layer": ("layer",),
    "bag": ("bag",),
}


def generate_candidates(
    items: Iterable[Any],
    max_candidates: int = 5000,
) -> list[OutfitCandidate]:
    """Build valid garment combinations in stable order with a hard upper bound.

    Items need a ``category`` attribute; ``id`` is recommended for stable
    de-duplication.  Unavailable items and duplicate item identities are
    automatically excluded.

    For each base skeleton, optional layers, bags, dupatta, and jewelry
    are added as alternative candidates rather than as a Cartesian
    multiplication that could starve other skeleton forms.
    """
    if max_candidates < 1:
        return []

    available = [item for item in items if _value(item, "is_available", True)]
    by_category: dict[str, list[Any]] = {}
    for item in available:
        category = _value(item, "category")
        if isinstance(category, str):
            by_category.setdefault(category.strip().lower(), []).append(item)

    # Stable ordering makes candidate results reproducible regardless of
    # DB row order.
    for category_items in by_category.values():
        category_items.sort(key=lambda item: str(_value(item, "id", "")))

    candidates: list[OutfitCandidate] = []
    seen: set[tuple[str, ...]] = set()

    has_shoes = bool(by_category.get("shoes"))

    for skeleton_name, raw_requirements in _SKELETONS:
        # If no shoes are available in the items, allow 2-piece / 1-piece looks without shoes
        if not has_shoes:
            requirements = tuple(req for req in raw_requirements if "shoes" not in req)
        else:
            requirements = raw_requirements

        choices = [
            [
                item
                for category in accepted
                for item in by_category.get(category, [])
            ]
            for accepted in requirements
        ]
        if any(not group for group in choices):
            continue

        for combination in product(*choices):
            # Build the base slot map
            if skeleton_name == "top_bottom":
                base_slots: dict[str, Any] = {
                    "top": combination[0],
                    "bottom": combination[1],
                }
                if len(combination) > 2:
                    base_slots["shoes"] = combination[2]
            elif skeleton_name == "dress":
                base_slots = {"dress": combination[0]}
                if len(combination) > 1:
                    base_slots["shoes"] = combination[1]
            elif skeleton_name == "saree":
                base_slots = {"saree": combination[0]}
                if len(combination) > 1:
                    base_slots["shoes"] = combination[1]
            else:  # ethnic_set
                base_slots = {"ethnic_set": combination[0]}
                if len(combination) > 1:
                    base_slots["shoes"] = combination[1]

            # Reject combinations where the same item appears twice
            if len({_extract_item_id(item) for item in base_slots.values()}) != len(base_slots):
                continue

            # Build variant list: base + optional single-item additions
            variants: list[tuple[dict[str, Any], str]] = [
                (base_slots, skeleton_name)
            ]

            base_ids = {_extract_item_id(item) for item in base_slots.values()}

            for slot, categories in _OPTIONAL_CATEGORIES.items():
                for optional_item in (
                    item
                    for category in categories
                    for item in by_category.get(category, [])
                ):
                    if _extract_item_id(optional_item) in base_ids:
                        continue
                    variants.append(
                        ({**base_slots, slot: optional_item}, skeleton_name)
                    )

            # Dupatta is optional for ethnic_set and saree looks
            if skeleton_name in ("ethnic_set", "saree"):
                for accessory in by_category.get("dupatta", []):
                    if _extract_item_id(accessory) not in base_ids:
                        variants.append(
                            ({**base_slots, "dupatta": accessory}, skeleton_name)
                        )

            # Jewelry is optional for saree looks
            if skeleton_name == "saree":
                for jewel in by_category.get("jewelry", []):
                    if _extract_item_id(jewel) not in base_ids:
                        variants.append(
                            ({**base_slots, "jewelry": jewel}, skeleton_name)
                        )

            for slots, variant_name in variants:
                identity = tuple(
                    sorted(_extract_item_id(item) for item in slots.values())
                )
                if identity in seen:
                    continue
                seen.add(identity)
                candidates.append(
                    OutfitCandidate(slots=slots, skeleton=variant_name)
                )
                if len(candidates) >= max_candidates:
                    return candidates

    return candidates
