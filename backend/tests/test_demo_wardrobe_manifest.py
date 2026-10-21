"""Automated tests validating outfit recommendation fixes against the demo wardrobe manifest.

Fixture source: tests/fixtures/test_wardrobe_manifest.csv
Validates:
- All 8 occasions and 6 vibes, including ranking divergence on vibe changes
- Wedding and ethnic shoe restrictions, and exclusion of casual streetwear from weddings
- Invalid kurti + Western skirt pairing rejection
- Sweater and hoodie layering restrictions
- Two loud patterns rejection (anti-clash)
- Conditional stretch rules (present, failing, and missing attributes)
- Legacy-only row normalization
- Unavailable items never appearing in any generated outfit
- Deterministic repeated generation with seeded execution
- Complete pool evaluation without false 'no results' from premature truncation
- Elegant looks (satin/silk) shoe restrictions
"""

import csv
import os
from pathlib import Path
from typing import Any

import pytest

from app.styling.explain import explain_outfit
from app.styling.features import feature_scores
from app.styling.generator import generate_outfits
from app.styling.rules import (
    check_pairing_graph,
    check_pattern_clash,
    get_item_valid_occasions,
    hard_filter_candidate,
    is_item_available,
    item_occasion_match,
)
from app.styling.skeletons import OutfitCandidate
from app.styling.taxonomy import (
    PieceRole,
    canonical_occasion,
    normalize_manifest_item,
)


MANIFEST_PATH = Path(__file__).parent / "fixtures" / "test_wardrobe_manifest.csv"


def load_manifest_items() -> list[dict[str, Any]]:
    """Load and normalize all rows from the wardrobe manifest CSV."""
    assert MANIFEST_PATH.exists(), f"Manifest fixture missing at {MANIFEST_PATH}"
    items = []
    with open(MANIFEST_PATH, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            normalized = normalize_manifest_item(row)
            items.append(normalized)
    return items


@pytest.fixture(scope="module")
def manifest_items() -> list[dict[str, Any]]:
    return load_manifest_items()


@pytest.fixture(scope="module")
def manifest_by_piece_id(manifest_items) -> dict[str, dict[str, Any]]:
    by_piece = {}
    for it in manifest_items:
        # Use filename prefix without extension, or piece_id
        fn = it.get("id", "")
        key = fn.replace(".jpg", "") if fn.endswith(".jpg") else it.get("piece_id", "")
        by_piece[key] = it
    return by_piece


# ---------------------------------------------------------------------------
# 1. Unavailable Items Never Appear
# ---------------------------------------------------------------------------


def test_unavailable_items_never_appear(manifest_items):
    """Items marked unavailable (available=false) must never appear in any generated outfit."""
    unavailable_ids = {it["id"] for it in manifest_items if not is_item_available(it)}
    assert "tshirt_03.jpg" in unavailable_ids
    assert "jacket_02.jpg" in unavailable_ids

    occasions = ["casual", "college", "work", "party", "date_night", "gym", "festive", "wedding"]
    for occ in occasions:
        outfits = generate_outfits(manifest_items, occasion=occ, season="all_season", limit=10, seed=42)
        for outfit in outfits:
            for it_id in outfit.item_ids:
                assert it_id not in unavailable_ids, f"Unavailable item {it_id} found in {occ} outfit"


# ---------------------------------------------------------------------------
# 2. Legacy-Only Normalization
# ---------------------------------------------------------------------------


def test_legacy_only_normalization(manifest_items, manifest_by_piece_id):
    """Legacy-only manifest rows must normalize cleanly into canonical slots and categories."""
    legacy_keys = [
        "tshirt_03", "kurti_03", "palazzo_01", "midi_dress_02",
        "saree_01", "jacket_01", "sneakers_01", "chappals_01",
    ]
    for key in legacy_keys:
        item = manifest_by_piece_id.get(key)
        assert item is not None, f"Legacy item {key} missing from manifest"
        assert item.get("slot") in {"top", "bottom", "ethnic_bottom", "dress", "saree", "ethnic_set", "layer", "shoes"}
        assert item.get("category") in {"top", "bottom", "ethnic_bottom", "dress", "saree", "ethnic_set", "layer", "shoes"}
        assert isinstance(item.get("formality"), int)


# ---------------------------------------------------------------------------
# 3. All Eight Occasions and Six Vibes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("occasion", [
    "casual", "college", "work", "party", "date_night", "gym", "festive", "wedding"
])
def test_all_occasions_valid_and_consistent(manifest_items, occasion):
    """Every generated outfit for each of the 8 canonical occasions must satisfy hard filters."""
    outfits = generate_outfits(manifest_items, occasion=occasion, season="all_season", limit=6, seed=42)
    # Some occasions in a specific capsule may have 0 or more valid outfits; all returned must be valid
    for outfit in outfits:
        assert hard_filter_candidate(outfit, occasion=occasion, season="all_season"), (
            f"Outfit {outfit.item_ids} violated hard filters for occasion {occasion}"
        )


@pytest.mark.parametrize("vibe", [
    "minimal", "classic", "streetwear", "romantic", "bohemian", "elegant"
])
def test_all_vibes_generate_valid_looks(manifest_items, vibe):
    """All 6 supported vibes must produce valid outfits without breaking hard constraints."""
    outfits = generate_outfits(
        manifest_items,
        occasion="casual",
        season="all_season",
        vibe=vibe,
        limit=5,
        seed=42,
    )
    assert len(outfits) > 0
    for outfit in outfits:
        assert hard_filter_candidate(outfit, occasion="casual", season="all_season")


def test_vibe_changes_ranking_meaningfully(manifest_items):
    """Selected vibes must meaningfully reorder plausible candidates without overriding rules."""
    streetwear_outfits = generate_outfits(
        manifest_items,
        occasion="casual",
        season="all_season",
        vibe="streetwear",
        limit=5,
        seed=42,
    )
    romantic_outfits = generate_outfits(
        manifest_items,
        occasion="casual",
        season="all_season",
        vibe="romantic",
        limit=5,
        seed=42,
    )
    minimal_outfits = generate_outfits(
        manifest_items,
        occasion="casual",
        season="all_season",
        vibe="minimal",
        limit=5,
        seed=42,
    )

    assert len(streetwear_outfits) > 0
    assert len(romantic_outfits) > 0
    assert len(minimal_outfits) > 0

    # Top items must differ between distinct vibes when multiple valid alternatives exist
    street_top_items = set(streetwear_outfits[0].item_ids)
    romantic_top_items = set(romantic_outfits[0].item_ids)
    minimal_top_items = set(minimal_outfits[0].item_ids)

    # At least two vibes must produce different top looks
    assert not (street_top_items == romantic_top_items == minimal_top_items), (
        "Vibes had zero impact on ranking; expected different top recommendations."
    )


# ---------------------------------------------------------------------------
# 4. Wedding / Ethnic Shoe Restrictions & Streetwear Exclusion
# ---------------------------------------------------------------------------


def test_streetwear_at_wedding_strictly_forbidden(manifest_items):
    """Casual streetwear pieces (t-shirts, hoodies, cargo, casual sneakers) must never appear at weddings."""
    wedding_outfits = generate_outfits(manifest_items, occasion="wedding", season="all_season", limit=8, seed=42)
    assert len(wedding_outfits) > 0, "Expected at least one valid wedding look from manifest"

    forbidden_wedding_items = {
        "tshirt_01.jpg", "tshirt_02.jpg", "hoodie_01.jpg", "trousers_casual_01.jpg",
        "shorts_01.jpg", "sneakers_01.jpg", "sneakers_02.jpg", "coord_set_01.jpg"
    }

    for outfit in wedding_outfits:
        for it_id in outfit.item_ids:
            assert it_id not in forbidden_wedding_items, (
                f"Streetwear item {it_id} was recommended for a wedding!"
            )


def test_ethnic_and_saree_footwear_restrictions(manifest_by_piece_id):
    """Traditional sets, sarees, and ethnic bottoms must NEVER pair with sneakers or loafers."""
    saree = manifest_by_piece_id["saree_02"]
    sneakers = manifest_by_piece_id["sneakers_01"]
    heels = manifest_by_piece_id["heels_01"]
    jutti = manifest_by_piece_id["jutti_01"]

    # Saree + sneakers: rejected
    saree_sneakers = OutfitCandidate(skeleton="saree", slots={"saree": saree, "shoes": sneakers})
    assert not check_pairing_graph(saree_sneakers, occasion="wedding")

    # Saree + heels / juttis: accepted
    saree_heels = OutfitCandidate(skeleton="saree", slots={"saree": saree, "shoes": heels})
    assert check_pairing_graph(saree_heels, occasion="wedding")

    saree_jutti = OutfitCandidate(skeleton="saree", slots={"saree": saree, "shoes": jutti})
    assert check_pairing_graph(saree_jutti, occasion="wedding")

    # Kurti set + sneakers: rejected
    kurti_set = manifest_by_piece_id["kurti_set_01"]
    set_sneakers = OutfitCandidate(skeleton="ethnic_set", slots={"ethnic_set": kurti_set, "shoes": sneakers})
    assert not check_pairing_graph(set_sneakers, occasion="festive")

    # Salwar + sneakers: rejected
    salwar = manifest_by_piece_id["salwar_01"]
    kurti = manifest_by_piece_id["kurti_01"]
    salwar_sneakers = OutfitCandidate(skeleton="top_bottom", slots={"top": kurti, "ethnic_bottom": salwar, "shoes": sneakers})
    assert not check_pairing_graph(salwar_sneakers, occasion="festive")


# ---------------------------------------------------------------------------
# 5. Invalid Kurti + Western Skirt Pairings
# ---------------------------------------------------------------------------


def test_kurti_western_skirt_pairing_rejected(manifest_by_piece_id):
    """Kurti paired with a Western skirt must be rejected."""
    kurti = manifest_by_piece_id["kurti_01"]
    skirt_floral = manifest_by_piece_id["skirt_01"]
    skirt_satin = manifest_by_piece_id["skirt_02"]
    heels = manifest_by_piece_id["heels_01"]

    bad_look1 = OutfitCandidate(skeleton="top_bottom", slots={"top": kurti, "bottom": skirt_floral, "shoes": heels})
    assert not check_pairing_graph(bad_look1, occasion="casual")

    bad_look2 = OutfitCandidate(skeleton="top_bottom", slots={"top": kurti, "bottom": skirt_satin, "shoes": heels})
    assert not check_pairing_graph(bad_look2, occasion="casual")


# ---------------------------------------------------------------------------
# 6. Sweater & Hoodie Layering Restrictions
# ---------------------------------------------------------------------------


def test_layer_over_hoodie_rejected(manifest_by_piece_id):
    """Layer over a hoodie is strictly rejected."""
    hoodie = manifest_by_piece_id["hoodie_01"]
    jacket = manifest_by_piece_id["jacket_01"]
    cardigan = manifest_by_piece_id["cardigan_01"]
    jeans = manifest_by_piece_id["jeans_01"]
    sneakers = manifest_by_piece_id["sneakers_02"]

    hoodie_jacket = OutfitCandidate(
        skeleton="top_bottom",
        slots={"top": hoodie, "bottom": jeans, "layer": jacket, "shoes": sneakers},
    )
    assert not check_pairing_graph(hoodie_jacket, occasion="casual")

    hoodie_cardigan = OutfitCandidate(
        skeleton="top_bottom",
        slots={"top": hoodie, "bottom": jeans, "layer": cardigan, "shoes": sneakers},
    )
    assert not check_pairing_graph(hoodie_cardigan, occasion="casual")


def test_layer_over_sweater_restrictions(manifest_by_piece_id):
    """Layer over sweater is rejected except where the approved rule permits it (blazer over fine-knit)."""
    sweater = manifest_by_piece_id["sweater_01"]  # knit_gauge=fine
    cardigan = manifest_by_piece_id["cardigan_01"]
    jacket = manifest_by_piece_id["jacket_01"]  # denim jacket (not a blazer)
    jeans = manifest_by_piece_id["jeans_01"]
    mules = manifest_by_piece_id["mules_01"]

    # Denim jacket over fine sweater: rejected
    look1 = OutfitCandidate(
        skeleton="top_bottom",
        slots={"top": sweater, "bottom": jeans, "layer": jacket, "shoes": mules},
    )
    assert not check_pairing_graph(look1, occasion="casual")

    # Cardigan over fine sweater: rejected
    look2 = OutfitCandidate(
        skeleton="top_bottom",
        slots={"top": sweater, "bottom": jeans, "layer": cardigan, "shoes": mules},
    )
    assert not check_pairing_graph(look2, occasion="casual")

    # Blazer over fine sweater: approved
    blazer = {
        "id": "blazer_test",
        "category": "layer",
        "slot": "layer",
        "role": PieceRole.LAYER,
        "sub_category": "blazer",
        "is_available": True,
        "formality": 3,
    }
    look3 = OutfitCandidate(
        skeleton="top_bottom",
        slots={"top": sweater, "bottom": jeans, "layer": blazer, "shoes": mules},
    )
    assert check_pairing_graph(look3, occasion="work")


# ---------------------------------------------------------------------------
# 7. Pattern Clash (Two Loud Patterns)
# ---------------------------------------------------------------------------


def test_two_loud_patterns_clash_rejected(manifest_by_piece_id):
    """Multiple loud patterns (e.g. block-print kurti + block-print palazzo) must be rejected."""
    kurti_loud = manifest_by_piece_id["kurti_02"]      # block_print
    palazzo_loud = manifest_by_piece_id["palazzo_02"]  # block_print
    palazzo_solid = manifest_by_piece_id["palazzo_01"] # solid
    mules = manifest_by_piece_id["mules_01"]

    clashing_candidate = OutfitCandidate(
        skeleton="top_bottom",
        slots={"top": kurti_loud, "ethnic_bottom": palazzo_loud, "shoes": mules},
    )
    assert not check_pattern_clash(clashing_candidate)

    harmonic_candidate = OutfitCandidate(
        skeleton="top_bottom",
        slots={"top": kurti_loud, "ethnic_bottom": palazzo_solid, "shoes": mules},
    )
    assert check_pattern_clash(harmonic_candidate)


# ---------------------------------------------------------------------------
# 8. Conditional Stretch Rules (Present, Failing, and Missing Attributes)
# ---------------------------------------------------------------------------


def test_conditional_stretch_tshirt_work(manifest_by_piece_id):
    """T-shirt work stretch: solid tee passes, graphic tee fails."""
    tshirt_solid = manifest_by_piece_id["tshirt_01"]
    tshirt_graphic = manifest_by_piece_id["tshirt_02"]

    assert item_occasion_match(tshirt_solid, "work") is True
    assert item_occasion_match(tshirt_graphic, "work") is False


def test_conditional_stretch_tank_date_night(manifest_by_piece_id):
    """Tank date_night stretch: satin cami passes, missing fabric fails."""
    tank_missing_fabric = manifest_by_piece_id["tank_01"]  # fabric is absent/rib
    tank_satin = manifest_by_piece_id["tank_02"]          # fabric=satin

    assert item_occasion_match(tank_missing_fabric, "date_night") is False
    assert item_occasion_match(tank_satin, "date_night") is True


def test_conditional_stretch_jeans_work(manifest_by_piece_id):
    """Jeans work stretch: dark wash passes, light wash fails, missing wash fails."""
    jeans_dark = manifest_by_piece_id["jeans_01"]   # wash=dark
    jeans_light = manifest_by_piece_id["jeans_02"]  # wash=light
    jeans_missing = manifest_by_piece_id["jeans_03"]# wash omitted

    assert item_occasion_match(jeans_dark, "work") is True
    assert item_occasion_match(jeans_light, "work") is False
    assert item_occasion_match(jeans_missing, "work") is False


def test_conditional_stretch_shorts_party(manifest_by_piece_id):
    """Shorts party stretch: missing fabric/pattern must NOT be granted."""
    shorts = manifest_by_piece_id["shorts_01"]
    assert item_occasion_match(shorts, "party") is False


def test_conditional_stretch_kurti_set_wedding(manifest_by_piece_id):
    """Kurti set wedding stretch: heavy velvet set passes, light pastel set fails."""
    kurti_set_light = manifest_by_piece_id["kurti_set_01"]  # formality=3, light embellishment
    kurti_set_heavy = manifest_by_piece_id["kurti_set_02"]  # formality=4, heavy embellishment

    assert item_occasion_match(kurti_set_light, "wedding") is False
    assert item_occasion_match(kurti_set_heavy, "wedding") is True


# ---------------------------------------------------------------------------
# 9. Saree Companion Requirement
# ---------------------------------------------------------------------------


def test_saree_companion_requirement(manifest_by_piece_id):
    """Saree without stitched blouse (saree_01) must pair with a blouse companion."""
    saree_no_blouse = manifest_by_piece_id["saree_01"]
    blouse = manifest_by_piece_id["blouse_01"]
    jutti = manifest_by_piece_id["jutti_01"]

    # Without blouse: rejected
    orphan_saree = OutfitCandidate(skeleton="saree", slots={"saree": saree_no_blouse, "shoes": jutti})
    assert not check_pairing_graph(orphan_saree, occasion="wedding")

    # With blouse: accepted
    paired_saree = OutfitCandidate(skeleton="saree", slots={"saree": saree_no_blouse, "top": blouse, "shoes": jutti})
    assert check_pairing_graph(paired_saree, occasion="wedding")


# ---------------------------------------------------------------------------
# 10. Elegant Looks Shoes Restrictions
# ---------------------------------------------------------------------------


def test_elegant_looks_shoe_restrictions(manifest_by_piece_id):
    """Elegant combinations (satin slip skirt or satin cami) must NEVER receive sneakers."""
    satin_skirt = manifest_by_piece_id["skirt_02"]
    satin_cami = manifest_by_piece_id["tank_02"]
    sneakers = manifest_by_piece_id["sneakers_01"]
    heels = manifest_by_piece_id["heels_01"]

    elegant_sneakers = OutfitCandidate(
        skeleton="top_bottom",
        slots={"top": satin_cami, "bottom": satin_skirt, "shoes": sneakers},
    )
    assert not check_pairing_graph(elegant_sneakers, occasion="date_night")

    elegant_heels = OutfitCandidate(
        skeleton="top_bottom",
        slots={"top": satin_cami, "bottom": satin_skirt, "shoes": heels},
    )
    assert check_pairing_graph(elegant_heels, occasion="date_night")


# ---------------------------------------------------------------------------
# 11. Deterministic Repeated Generation
# ---------------------------------------------------------------------------


def test_deterministic_repeated_generation(manifest_items):
    """Identical seed and inputs must generate identical ranked candidates across multiple runs."""
    run1 = generate_outfits(manifest_items, occasion="work", season="all_season", seed=777, limit=5)
    run2 = generate_outfits(manifest_items, occasion="work", season="all_season", seed=777, limit=5)

    assert len(run1) == len(run2)
    for c1, c2 in zip(run1, run2):
        assert c1.item_ids == c2.item_ids
        assert c1.skeleton == c2.skeleton


# ---------------------------------------------------------------------------
# 12. No False 'No Results' from Premature Truncation
# ---------------------------------------------------------------------------


def test_no_false_no_results_evaluates_complete_pool(manifest_items):
    """The complete candidate pool must be threshold-filtered so higher-quality candidates are not truncated."""
    # Run with a quality threshold of 0.60
    candidates = generate_outfits(
        manifest_items,
        occasion="work",
        season="all_season",
        min_score=0.60,
        limit=5,
        seed=42,
    )
    assert len(candidates) > 0, "Complete candidate pool should have found qualifying work outfits"
    for cand in candidates:
        assert hard_filter_candidate(cand, occasion="work", season="all_season")


# ---------------------------------------------------------------------------
# 13. Date-Night & Party Vibe Ranking and Top-Look Divergence
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("occasion", ["date_night", "party"])
def test_date_night_party_ranking_across_all_six_vibes(manifest_items, occasion):
    """Date-night and party across all six vibes must satisfy hard rules and produce distinct top looks."""
    vibes = ["classic", "minimal", "romantic", "bohemian", "streetwear", "elegant"]
    top_look_signatures = {}

    for v in vibes:
        outfits = generate_outfits(manifest_items, occasion=occasion, season="all_season", vibe=v, limit=3, seed=42)
        assert len(outfits) > 0, f"Expected outfits for {occasion} with vibe {v}"

        # Every returned candidate must strictly satisfy hard filters
        for outfit in outfits:
            assert hard_filter_candidate(outfit, occasion=occasion, season="all_season"), (
                f"Candidate {outfit.item_ids} violated hard filters for {occasion} under vibe {v}"
            )

        top_look_signatures[v] = tuple(sorted(outfits[0].item_ids))

    # Verify that the engine no longer collapses to a single top outfit across all vibes
    unique_top_looks = set(top_look_signatures.values())
    assert len(unique_top_looks) >= 4, (
        f"Expected at least 4 distinct top looks across 6 vibes for {occasion}, but got {len(unique_top_looks)}: {top_look_signatures}"
    )


def test_vibe_specific_top_look_changes_when_comparable_alternatives_exist(manifest_items):
    """When comparable valid pieces exist, selected vibe meaningfully favors compatible wardrobe pieces."""
    boho_outfits = generate_outfits(manifest_items, occasion="date_night", season="all_season", vibe="bohemian", limit=3, seed=42)
    romantic_outfits = generate_outfits(manifest_items, occasion="date_night", season="all_season", vibe="romantic", limit=3, seed=42)
    classic_outfits = generate_outfits(manifest_items, occasion="date_night", season="all_season", vibe="classic", limit=3, seed=42)
    minimal_outfits = generate_outfits(manifest_items, occasion="date_night", season="all_season", vibe="minimal", limit=3, seed=42)

    # Bohemian top look should feature authentic bohemian pieces from the wardrobe
    boho_top_ids = set(boho_outfits[0].item_ids)
    boho_wardrobe_pieces = {"crop_top_02.jpg", "skirt_01.jpg", "maxi_dress_01.jpg", "palazzo_02.jpg", "shrug_01.jpg"}
    assert boho_top_ids & boho_wardrobe_pieces, f"Bohemian look {boho_top_ids} did not include any bohemian pieces"

    # Romantic top look should feature romantic pieces
    romantic_top_ids = set(romantic_outfits[0].item_ids)
    romantic_wardrobe_pieces = {"midi_dress_01.jpg", "crop_top_01.jpg", "tank_02.jpg", "skirt_01.jpg"}
    assert romantic_top_ids & romantic_wardrobe_pieces, f"Romantic look {romantic_top_ids} did not include any romantic pieces"

    # Classic top look should feature tailored classic pieces (e.g. heels_01 or blouse_01)
    classic_top_ids = set(classic_outfits[0].item_ids)
    classic_pieces = {"heels_01.jpg", "blouse_01.jpg", "midi_dress_02.jpg", "mini_dress_01.jpg"}
    assert classic_top_ids & classic_pieces, f"Classic look {classic_top_ids} did not include classic pieces"

    # The top look for bohemian must differ from classic
    assert boho_top_ids != classic_top_ids, "Bohemian top look identical to classic top look"


# ---------------------------------------------------------------------------
# 14. Stable Behavior & Honest Signal on Weak Vibe Match
# ---------------------------------------------------------------------------


def test_stable_behavior_when_no_strong_match_for_vibe(manifest_items):
    """When the wardrobe lacks strong pieces for a vibe (e.g. streetwear for date_night), behave stably and report honestly."""
    outfits = generate_outfits(manifest_items, occasion="date_night", season="all_season", vibe="streetwear", limit=3, seed=42)
    assert len(outfits) > 0, "Engine should stably produce valid fallback outfits"

    # All returned outfits must still satisfy hard filters (never break rules to force a vibe)
    for outfit in outfits:
        assert hard_filter_candidate(outfit, occasion="date_night", season="all_season")

    top = outfits[0]
    scores = feature_scores(top, occasion="date_night", season="all_season", vibe="streetwear")
    # Streetwear coverage in date_night is limited; vibe_affinity must honestly reflect this (<= 0.45)
    assert scores["vibe_affinity"] <= 0.45, f"Expected honest moderate/low vibe affinity, got {scores['vibe_affinity']}"

    # Grounded explanation should explain honestly rather than claim a strong aesthetic match
    reasons = explain_outfit(top, occasion="date_night", season="all_season", vibe="streetwear")
    assert any("limited streetwear options" in r.lower() or "occasion fit" in r.lower() for r in reasons), (
        f"Expected explanation to honestly mention limited options or occasion fit; got: {reasons}"
    )


# ---------------------------------------------------------------------------
# 15. Diversity Among Returned Outfits Without Invalidating Hard Rules
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("occasion", ["date_night", "party"])
def test_diversity_among_returned_outfits_without_invalidating_hard_rules(manifest_items, occasion):
    """Returned recommendations must vary core garments and silhouettes while strictly obeying rules."""
    outfits = generate_outfits(manifest_items, occasion=occasion, season="all_season", vibe="classic", limit=3, seed=42)
    assert len(outfits) >= 3

    # All returned outfits must satisfy hard filters
    for outfit in outfits:
        assert hard_filter_candidate(outfit, occasion=occasion, season="all_season")

    # Core signatures must be distinct across the top returned looks
    core_signatures = [outfit.core_signature for outfit in outfits]
    assert len(set(core_signatures)) == len(outfits), (
        f"Found duplicate core signatures among recommendations: {core_signatures}"
    )

    # Silhouettes across the recommendations should not all be identical
    skeletons = {outfit.skeleton for outfit in outfits}
    assert len(skeletons) >= 2, f"Expected silhouette diversity across recommendations, got: {skeletons}"

