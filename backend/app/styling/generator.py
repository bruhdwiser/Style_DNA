"""Outfit generation with deterministic MMR diversification and rule scoring.

Ported from StyleSenseAI outfits/generator.py — the main entry point for
outfit generation. Uses an injected seed for deterministic tie-breaks;
``random.Random(seed)`` provides stable shuffling without ambient I/O.

The engine must remain pure: no database calls, no HTTP, no file reads.
"""

from __future__ import annotations

import random
from typing import Any

from app.styling.features import feature_scores, score_outfit
from app.styling.rules import hard_filter_candidate
from app.styling.skeletons import OutfitCandidate, generate_candidates


def _coerce_item(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, item.get(key.replace("_", ""), default))
    return getattr(item, key, default)


def _signature(candidate: OutfitCandidate) -> set[str]:
    """Build a lowered set of item traits for similarity measurement."""
    signature: set[str] = set()
    for item in candidate.slots.values():
        category = str(_coerce_item(item, "category", ""))
        style = str(_coerce_item(item, "style", ""))
        color = str(_coerce_item(item, "color", ""))
        item_id = str(_coerce_item(item, "id", ""))
        for value in (category, style, color, item_id):
            if value:
                signature.add(value.lower())
    return signature


def _similarity(a: OutfitCandidate, b: OutfitCandidate) -> float:
    """Jaccard similarity between two candidate signatures."""
    left = _signature(a)
    right = _signature(b)
    if not left and not right:
        return 0.0
    if not left or not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def _silhouette(candidate: OutfitCandidate) -> tuple[str, ...]:
    """Tuple of slot:subtype identifiers representing structural silhouette."""
    sil = []
    for slot, item in sorted(candidate.slots.items()):
        subcat = str(
            _coerce_item(item, "sub_category")
            or _coerce_item(item, "subtype")
            or _coerce_item(item, "category")
            or ""
        ).lower()
        sil.append(f"{slot}:{subcat}")
    return tuple(sil)


def _silhouette_similarity(a: OutfitCandidate, b: OutfitCandidate) -> float:
    """Measure structural silhouette overlap between two candidates."""
    sil_a = set(_silhouette(a))
    sil_b = set(_silhouette(b))
    if not sil_a or not sil_b:
        return 0.0
    return len(sil_a & sil_b) / len(sil_a | sil_b)


CORE_REPEAT_PENALTY: float = 0.45


def _mmr_diversify(
    ranked: list[tuple[float, OutfitCandidate]],
    *,
    limit: int,
    seed: int | None = 0,
    is_shuffle: bool = False,
    exclude_core_signatures: set[frozenset[tuple[str, str]]] | None = None,
) -> list[tuple[float, OutfitCandidate]]:
    """Maximal Marginal Relevance diversification with deterministic tie-breaking.

    Selects up to *limit* candidates, balancing quality against novelty and
    silhouette/core diversity relative to already-selected candidates.
    """
    if not ranked:
        return []

    # Decouple stochasticity from random seed: normal requests (is_shuffle=False)
    # remain strictly deterministic even if a non-zero seed is passed.
    rng = random.Random(seed if is_shuffle else 0)
    is_stochastic = is_shuffle

    candidates_pool = list(ranked)

    # In shuffle mode, strictly exclude already seen core signatures without silent fallback
    if is_shuffle and exclude_core_signatures:
        candidates_pool = [
            item for item in candidates_pool
            if item[1].core_signature not in exclude_core_signatures
        ]

    if not candidates_pool:
        return []

    if is_stochastic:
        jittered = [
            (round(score + rng.uniform(-0.02, 0.02), 4), cand)
            for score, cand in candidates_pool
        ]
        jittered.sort(
            key=lambda item: (
                round(-item[0], 4),
                tuple(sorted(item[1].core_signature)),
                item[1].item_ids,
            )
        )
        anchor = rng.choice(jittered[:min(3, len(jittered))])
        selected = [anchor]
        remaining = [item for item in jittered if item[1] != anchor[1]]
    else:
        # Sort deterministically with stable tiebreakers:
        # 1. descending score (-item[0])
        # 2. core signature tuple
        # 3. full item_ids tuple
        candidates_pool.sort(
            key=lambda item: (
                round(-item[0], 4),
                tuple(sorted(item[1].core_signature)),
                item[1].item_ids,
            )
        )
        selected = [candidates_pool[0]]
        remaining = list(candidates_pool[1:])

    while len(selected) < min(limit, len(candidates_pool)) and remaining:
        best_index = -1
        best_value = float("-inf")
        for index, (score, candidate) in enumerate(remaining):
            max_sim = (
                max(
                    _similarity(candidate, chosen_candidate)
                    for _, chosen_candidate in selected
                )
                if selected
                else 0.0
            )
            max_sil_sim = (
                max(
                    _silhouette_similarity(candidate, chosen_candidate)
                    for _, chosen_candidate in selected
                )
                if selected
                else 0.0
            )
            exact_sil_count = sum(
                1
                for _, chosen_candidate in selected
                if _silhouette(candidate) == _silhouette(chosen_candidate)
            )

            # Core repetition penalty: prioritize distinct core combinations before repeating cores
            core_overlap = any(
                candidate.core_signature == chosen_candidate.core_signature
                for _, chosen_candidate in selected
            )
            core_penalty = CORE_REPEAT_PENALTY if core_overlap else 0.0

            # Combined diversity penalty
            diversity_penalty = (
                (0.20 * max_sim)
                + (0.35 * max_sil_sim)
                + (0.30 * exact_sil_count)
                + core_penalty
            )
            jitter = (
                rng.uniform(-0.015, 0.015)
                if is_stochastic
                else 0.0
            )

            mmr_value = (0.65 * score) - diversity_penalty + jitter
            if mmr_value > best_value:
                best_value = mmr_value
                best_index = index
        if best_index < 0:
            break
        selected.append(remaining.pop(best_index))
    return selected


def generate_outfits(
    items: list[Any],
    *,
    occasion: Any = "casual",
    season: Any = "all_season",
    vibe: str | None = None,
    vibes: list[str] | None = None,
    body_shape: str | None = None,
    attrs: dict[str, Any] | None = None,
    affinities: dict[str, Any] | None = None,
    seed: int | None = 0,
    limit: int = 8,
    max_candidates: int = 5000,
    is_shuffle: bool = False,
    exclude_core_signatures: set[frozenset[tuple[str, str]]] | None = None,
) -> list[OutfitCandidate]:
    """Generate and rank a diversified set of valid outfit candidates.

    This is the main entry point. Hard filters ensure outfit validity and occasion
    rules strictly dominate. If affinities are provided, a bounded Style DNA
    adjustment is applied to order candidates predictably according to user feedback.
    """
    from app.styling.learning import compute_outfit_affinity_adjustment

    skeletons = generate_candidates(items, max_candidates=max_candidates)
    valid = [
        candidate
        for candidate in skeletons
        if hard_filter_candidate(candidate, occasion, season)
    ]
    ranked: list[tuple[float, OutfitCandidate]] = []
    for candidate in valid:
        base_score = score_outfit(
            candidate,
            occasion=occasion,
            season=season,
            vibe=vibe,
            vibes=vibes,
            body_shape=body_shape,
            attrs=attrs,
            seed=seed,
        )
        if affinities:
            delta, _ = compute_outfit_affinity_adjustment(candidate, affinities)
            adjusted_score = round(max(0.0, min(1.0, base_score + delta)), 3)
        else:
            adjusted_score = base_score

        ranked.append((adjusted_score, candidate))

    if not ranked:
        return []
    ranked.sort(
        key=lambda item: (
            round(-item[0], 4),
            tuple(sorted(item[1].core_signature)),
            item[1].item_ids,
        )
    )
    diversified = _mmr_diversify(
        ranked,
        limit=limit,
        seed=seed,
        is_shuffle=is_shuffle,
        exclude_core_signatures=exclude_core_signatures,
    )
    return [candidate for _, candidate in diversified]


def generate_ranked_outfits(
    items: list[Any],
    *,
    occasion: Any = "casual",
    season: Any = "all_season",
    vibe: str | None = None,
    vibes: list[str] | None = None,
    body_shape: str | None = None,
    attrs: dict[str, Any] | None = None,
    seed: int | None = 0,
    limit: int = 8,
    max_candidates: int = 5000,
) -> list[tuple[float, OutfitCandidate]]:
    """Return ranked candidates, preserving score ordering before diversification."""
    skeletons = generate_candidates(items, max_candidates=max_candidates)
    valid = [
        candidate
        for candidate in skeletons
        if hard_filter_candidate(candidate, occasion, season)
    ]
    ranked: list[tuple[float, OutfitCandidate]] = []
    for candidate in valid:
        ranked.append((
            score_outfit(
                candidate,
                occasion=occasion,
                season=season,
                vibe=vibe,
                vibes=vibes,
                body_shape=body_shape,
                attrs=attrs,
                seed=seed,
            ),
            candidate,
        ))
    ranked.sort(
        key=lambda item: (
            round(-item[0], 4),
            tuple(sorted(item[1].core_signature)),
            item[1].item_ids,
        )
    )
    return ranked[:limit]
