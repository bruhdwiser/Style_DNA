"""Outfit generation and saved looks router.

Uses the pure Python rules engine to generate, score, diversify, explain,
and persist outfits and their item references.
All data access uses the authenticated user's client (preserving RLS).
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, Query

from ..core.config import settings
from ..core.exceptions import AppException
from ..core.security import get_current_token, get_current_user
from ..core.supabase import get_user_scoped_supabase_client
from ..schemas.outfit import (
    GenerateOutfitsRequest,
    GenerateOutfitsResponse,
    OutfitResponse,
    OutfitSlotItem,
    SavedOutfitsListResponse,
    SaveOutfitRequest,
    SaveOutfitResponse,
    UpdateOutfitTagsRequest,
    APPROVED_OUTFIT_TAGS,
    APPROVED_OUTFIT_TAGS_MAP,
    validate_and_normalize_tags,
    normalize_outfit_tags,
)
from ..schemas.style_dna import RecordOutfitEventRequest, OutfitEventResponse
from ..schemas.user import AuthenticatedUser
from ..styling.explain import explain_outfit
from ..styling.features import feature_scores, score_outfit
from ..styling.gaps import rank_gaps
from ..styling.generator import generate_outfits
from ..styling.learning import calculate_affinities, compute_outfit_affinity_adjustment
from ..styling.taxonomy import (
    calculate_slot_coverage,
    classify_outfit_core,
    canonical_occasion,
)
from ..styling.skeletons import CORE_SLOTS, OutfitCandidate, generate_candidates
from ..styling.rules import hard_filter_candidate
from .gaps import (
    _is_valid_uuid,
    _matches_audience,
    _matches_occasion,
    _matches_slot,
    _to_catalog_suggestion,
)

logger = logging.getLogger("flashfit.outfits")

router = APIRouter(prefix="/outfits", tags=["Outfits"])

STORAGE_BUCKET = "wardrobe"
SIGNED_URL_EXPIRY = 3600  # 1 hour


# ==============================================================================
# Helpers
# ==============================================================================


def _matches_season(product_seasons: Any, target_season: Optional[str]) -> bool:
    """Check if catalog product seasons match target season without asserting compatibility without evidence.

    Option 1 (Strict Evidence Policy):
    - If target_season is 'all_season', 'all', 'any', or empty, any product is accepted.
    - If a specific climate is requested (e.g. 'winter', 'summer', 'monsoon'), missing/empty seasons metadata
      is excluded because there is no evidence of suitability.
    - A product matches if its seasons explicitly include the target season (or recognized alias) or 'all_season'.
    """
    if not target_season:
        return True
    norm_target = str(target_season).strip().lower().replace(" ", "_")
    if norm_target in ("all_season", "all", "any"):
        return True

    if not product_seasons:
        return False  # Missing/empty metadata cannot be claimed compatible with specific seasons

    if isinstance(product_seasons, str):
        raw_list = [product_seasons]
    elif isinstance(product_seasons, (list, tuple, set)):
        raw_list = list(product_seasons)
    else:
        raw_list = [str(product_seasons)]

    norm_seasons = {str(s).strip().lower().replace(" ", "_") for s in raw_list if s}
    if not norm_seasons:
        return False

    from ..styling.rules import OUTFIT_RULE_CONFIG
    allowed = OUTFIT_RULE_CONFIG.get("season_aliases", {}).get(norm_target, {norm_target, "all_season"})
    return bool(norm_seasons & allowed) or "all_season" in norm_seasons


def _build_signed_view_url(client: Any, path: Optional[str]) -> Optional[str]:
    """Generate temporary signed view URL for private storage object."""
    if not path:
        return None
    try:
        res = client.storage.from_(STORAGE_BUCKET).create_signed_url(path, SIGNED_URL_EXPIRY)
        if isinstance(res, dict):
            return res.get("signedUrl") or res.get("signed_url")
        if hasattr(res, "signed_url"):
            return getattr(res, "signed_url")
    except Exception as exc:
        logger.debug(f"Unable to create signed URL for {path}: {exc}")
    return path


def _format_slot_item(
    raw_item: dict[str, Any],
    slot_name: str,
    client: Any,
    source_type: str = "wardrobe",
    product: Optional[dict[str, Any]] = None,
) -> OutfitSlotItem:
    if source_type == "catalog" or product is not None:
        p = product or raw_item
        p_id = str(p.get("id", ""))
        price_cents = p.get("price_cents")
        price = round(price_cents / 100.0, 2) if price_cents is not None else None
        return OutfitSlotItem(
            slot=slot_name,
            source_type="catalog",
            wardrobe_item_id=None,
            product_id=p_id,
            name=str(p.get("name", "Catalog Product")),
            category=str(p.get("category", slot_name)),
            sub_category=p.get("subtype"),
            primary_color=(p.get("color_tags") or [None])[0] if p.get("color_tags") else None,
            color_tags=p.get("color_tags") or [],
            fit=p.get("fit"),
            price=price,
            price_cents=price_cents,
            thumbnail_url=p.get("image_url"),
            image_url=p.get("image_url"),
        )

    storage_path = raw_item.get("storage_path") or ""
    thumbnail_path = raw_item.get("thumbnail_path") or storage_path

    signed_img = _build_signed_view_url(client, storage_path)
    signed_thumb = _build_signed_view_url(client, thumbnail_path) if thumbnail_path else signed_img

    name = (
        raw_item.get("sub_category")
        or raw_item.get("name")
        or raw_item.get("category", "Item")
    )

    return OutfitSlotItem(
        slot=slot_name,
        source_type="wardrobe",
        wardrobe_item_id=str(raw_item.get("id", "")),
        product_id=None,
        name=name.title() if isinstance(name, str) else "Item",
        category=raw_item.get("category", "top"),
        sub_category=raw_item.get("sub_category"),
        primary_color=raw_item.get("primary_color"),
        color_tags=raw_item.get("color_tags") or [],
        fit=raw_item.get("fit"),
        thumbnail_url=signed_thumb,
        image_url=signed_img,
    )


async def _rephrase_explanation_with_openrouter(
    items: list[OutfitSlotItem],
    reasons: list[str],
    occasion: str,
    vibe: Optional[str] = None,
    catalog_by_id: Optional[dict[str, dict]] = None,
) -> Optional[str]:
    """Generates an optional concise stylistic summary using OpenRouter when available.

    CRITICAL PRIVACY & GROUNDING GUARANTEES:
    - NEVER sends any body measurements, body type, or private profile metrics.
    - References only the concrete garment names, colors, categories, and occasion.
    - Validates every product UUID against the catalog; strips invalid links.
    - Falls back cleanly to None (keeping deterministic reasons) if OpenRouter fails.
    """
    if not settings.OPENROUTER_API_KEY or not settings.OPENROUTER_API_KEY.strip():
        return None

    item_facts = ", ".join(f"{it.name} ({it.category}, {it.primary_color or 'color'})" for it in items)
    reasons_text = "; ".join(reasons[:3])

    prompt = (
        f"You are a chic, encouraging fashion stylist. Synthesize these factual outfit elements for a {occasion} occasion "
        f"(vibe: {vibe or 'casual'}):\n"
        f"Garments: {item_facts}\n"
        f"Key styling reasons: {reasons_text}\n"
        "Provide a natural, 2-sentence styling summary explaining why this look works together. "
        "Do NOT invent new items or brands. Never mention body measurements or size."
    )

    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            res = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": settings.SITE_URL,
                    "X-Title": "StyleSense Fashion AI",
                },
                json={
                    "model": settings.OPENROUTER_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.5,
                    "max_tokens": 150,
                },
            )
            if res.status_code == 200:
                data = res.json()
                raw_text = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                if raw_text:
                    if catalog_by_id:
                        from .ai_chat import extract_and_sanitize_links
                        sanitized, _ = extract_and_sanitize_links(raw_text, catalog_by_id)
                        return sanitized
                    return raw_text
    except Exception as exc:
        logger.debug(f"OpenRouter optional outfit phrasing skipped: {exc}")
    return None


def _persist_outfit_and_items(
    client: Any,
    outfit_row: dict[str, Any],
    item_insert_rows: list[dict[str, Any]],
) -> bool:
    """Persist outfit and its item mappings atomically using PostgreSQL RPC save_outfit_with_items.

    Returns True if successfully persisted in a single transaction; False if persistence failed.
    Never returns True for an outfit ID whose database rows failed to persist, and refuses
    non-atomic multi-step fallbacks to guarantee no orphaned outfit rows are left behind.
    """
    outfit_id = outfit_row["id"]
    try:
        rpc_res = client.rpc(
            "save_outfit_with_items",
            {"p_outfit": outfit_row, "p_items": item_insert_rows},
        ).execute()
        if rpc_res and rpc_res.data:
            return True
        logger.error(
            f"Atomic persistence RPC save_outfit_with_items returned empty data for outfit {outfit_id}. "
            "Refusing non-atomic fallback."
        )
        return False
    except Exception as rpc_exc:
        logger.error(
            f"Atomic persistence via save_outfit_with_items failed for outfit {outfit_id}: {rpc_exc}. "
            "Refusing non-atomic fallback to guarantee no orphaned outfit rows are created. "
            "Deployment requirement: verify scripts/migrations/2026-10-21_save_outfit_rpc.sql is applied."
        )
        return False


# ==============================================================================
# Outfit Generation Endpoint
# ==============================================================================


@router.post(
    "/generate",
    response_model=GenerateOutfitsResponse,
    summary="Generate personalized outfits from user wardrobe",
)
async def generate_outfit_recommendations(
    body: GenerateOutfitsRequest,
    token: str = Depends(get_current_token),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Generates ranked, diversified outfits using the pure Python rules engine.

    - Loads caller's wardrobe items and profile through user-scoped Supabase client (RLS).
    - Missing profile is treated as a warning (engine uses neutral defaults).
    - Empty wardrobe returns a structured empty state.
    - Catalog completion is enabled by default; wardrobe_only=True is a strict opt-out.
    - Resolves shortfall: above-threshold wardrobe first, then eligible catalog items,
      then unique below-threshold wardrobe looks marked with warnings.
    - Persists generated outfits atomically, returning partial_results when fewer than limit.
    """
    client = get_user_scoped_supabase_client(token)

    # 1. Resolve effective catalog permission:
    # Catalog completion enabled by default; wardrobe_only=True is a strict opt-out.
    if body.wardrobe_only is True:
        effective_allow_catalog = False
    elif body.allow_one_new_item is False and body.wardrobe_only is False:
        effective_allow_catalog = False
    else:
        effective_allow_catalog = True

    # 2. Fetch caller's wardrobe items (enforced by RLS)
    try:
        wardrobe_res = (
            client.from_("wardrobe_items")
            .select("*")
            .eq("user_id", user.id)
            .execute()
        )
    except Exception as exc:
        logger.error(f"Failed to load wardrobe for user {user.id}: {exc}")
        raise AppException(
            message="Unable to load wardrobe items for outfit generation.",
            code="WARDROBE_LOAD_ERROR",
            status_code=500,
        )

    wardrobe_items: list[dict[str, Any]] = wardrobe_res.data or []

    # Check for empty wardrobe
    if not wardrobe_items:
        return GenerateOutfitsResponse(
            outfits=[],
            status="empty_wardrobe",
            message="Your wardrobe is empty. Add clothing items to your closet before generating outfits.",
            missing_slots=["top", "bottom", "shoes"],
        )

    # 3. Check for missing critical slots
    coverage = calculate_slot_coverage(wardrobe_items)
    critical_missing = coverage.get("critical_missing") or []

    if not coverage.get("is_ready_for_outfits") and critical_missing:
        # If user explicitly opted out of catalog completion:
        if not effective_allow_catalog:
            return GenerateOutfitsResponse(
                outfits=[],
                status="missing_required_slots",
                message="Your wardrobe is missing required items to build outfits for this occasion.",
                missing_slots=critical_missing,
            )

    # 4. Fetch caller's style profile (neutral styling defaults, never infer audience)
    profile_warning: Optional[str] = None
    body_shape: Optional[str] = None
    attrs: dict[str, Any] = {}

    try:
        profile_res = (
            client.from_("style_profiles")
            .select("*")
            .eq("user_id", user.id)
            .limit(1)
            .execute()
        )
        if profile_res.data and len(profile_res.data) > 0:
            profile = profile_res.data[0]
            body_shape = profile.get("body_type")
            guidance = profile.get("body_guidance") or {}
            attrs = guidance.get("recommendations") or {}
        else:
            profile_warning = "Style profile is incomplete. Generating outfits with neutral styling defaults."
    except Exception as exc:
        logger.warning(f"Could not load profile for user {user.id}: {exc}")
        profile_warning = "Could not load style profile; proceeding with neutral defaults."

    # 5. Format items for pure engine
    engine_items = []
    item_by_id: dict[str, dict[str, Any]] = {}
    for raw in wardrobe_items:
        raw_id = str(raw["id"])
        item_by_id[raw_id] = raw
        engine_items.append({
            "id": raw_id,
            "category": raw.get("slot") or raw.get("category", "top"),
            "slot": raw.get("slot", "top"),
            "sub_category": raw.get("sub_category"),
            "color": raw.get("primary_color"),
            "colors": raw.get("color_tags") or [],
            "fit": raw.get("fit"),
            "formality": raw.get("formality", 1),
            "occasions": raw.get("occasions") or [],
            "seasons": raw.get("seasons") or [],
            "styles": raw.get("style_tags") or [],
            "pattern": raw.get("pattern", "solid"),
            "neckline": raw.get("neckline"),
            "rise": raw.get("rise"),
            "length": raw.get("length"),
            "is_available": True,
            "source_type": "wardrobe",
        })

    # 6. Load caller's outfit events to derive Style DNA affinities
    affinities: dict[str, Any] = {}
    try:
        events_res = (
            client.from_("outfit_events")
            .select("event_type, metadata")
            .eq("user_id", user.id)
            .execute()
        )
        if events_res.data:
            affinities = calculate_affinities(events_res.data)
    except Exception as exc:
        logger.debug(f"Could not load events for Style DNA affinities: {exc}")

    occasion = canonical_occasion(body.occasion)
    season = body.season.strip().lower()

    # Unpack exclude_core_signatures if provided
    exclude_cores: set[frozenset[tuple[str, str]]] = set()
    if body.exclude_core_signatures:
        for sig in body.exclude_core_signatures:
            cleaned_pairs = []
            for item in sig:
                if isinstance(item, (list, tuple)) and len(item) == 2:
                    cleaned_pairs.append((str(item[0]).strip().lower(), str(item[1]).strip()))
            if cleaned_pairs:
                exclude_cores.add(frozenset(cleaned_pairs))

    # 7. Generate wardrobe-only candidates first
    wardrobe_candidates: list[OutfitCandidate] = []
    if coverage.get("is_ready_for_outfits"):
        wardrobe_candidates = generate_outfits(
            engine_items,
            occasion=occasion,
            season=season,
            vibe=body.vibe,
            vibes=body.vibes,
            body_shape=body_shape,
            attrs=attrs,
            affinities=affinities,
            seed=body.seed,
            limit=max(12, body.limit * 2),
            is_shuffle=body.is_shuffle,
            exclude_core_signatures=exclude_cores if body.is_shuffle else None,
        )

    # 8. Partition wardrobe candidates by quality threshold
    above_threshold_wardrobe: list[tuple[float, OutfitCandidate, dict[str, float], list[str]]] = []
    below_threshold_wardrobe: list[tuple[float, OutfitCandidate, dict[str, float], list[str]]] = []

    for cand in wardrobe_candidates:
        scores = feature_scores(
            cand,
            occasion=occasion,
            season=season,
            vibe=body.vibe,
            vibes=body.vibes,
            body_shape=body_shape,
            attrs=attrs,
        )
        base_score = float(
            score_outfit(
                cand,
                occasion=occasion,
                season=season,
                vibe=body.vibe,
                vibes=body.vibes,
                body_shape=body_shape,
                attrs=attrs,
            )
        )
        affinity_delta, _ = compute_outfit_affinity_adjustment(cand, affinities) if affinities else (0.0, [])
        total_score = round(max(0.0, min(1.0, base_score + affinity_delta)), 3)
        if affinities and affinities.get("total_events"):
            scores["style_dna"] = round(max(0.0, min(1.0, 0.5 + (affinity_delta / 0.16))), 3)

        reasons = explain_outfit(
            cand,
            occasion=occasion,
            season=season,
            body_shape=body_shape,
            attrs=attrs,
            affinities=affinities,
        )

        item_tuple = (total_score, cand, scores, reasons)
        if total_score >= body.min_quality_threshold:
            above_threshold_wardrobe.append(item_tuple)
        else:
            below_threshold_wardrobe.append(item_tuple)

    selected_looks: list[dict[str, Any]] = []
    chosen_core_sigs: set[frozenset[tuple[str, str]]] = set()
    chosen_item_sets: set[tuple[str, ...]] = set()

    # Pass 1: Prioritize distinct core wardrobe combinations up to body.limit
    for total_score, cand, scores, reasons in above_threshold_wardrobe:
        cand_item_sig = tuple(sorted(cand.item_ids))
        if cand_item_sig in chosen_item_sets:
            continue
        if cand.core_signature in chosen_core_sigs:
            continue
        selected_looks.append({
            "candidate": cand,
            "score": total_score,
            "scores": scores,
            "reasons": reasons,
            "source_type": "wardrobe",
            "is_below_threshold": False,
            "quality_warning": None,
            "catalog_product": None,
        })
        chosen_core_sigs.add(cand.core_signature)
        chosen_item_sets.add(cand_item_sig)
        if len(selected_looks) >= body.limit:
            break

    # Pass 2: If limit not met, allow unique peripheral variations (same core with different shoes/layers)
    if len(selected_looks) < body.limit:
        for total_score, cand, scores, reasons in above_threshold_wardrobe:
            cand_item_sig = tuple(sorted(cand.item_ids))
            if cand_item_sig in chosen_item_sets:
                continue
            selected_looks.append({
                "candidate": cand,
                "score": total_score,
                "scores": scores,
                "reasons": reasons,
                "source_type": "wardrobe",
                "is_below_threshold": False,
                "quality_warning": None,
                "catalog_product": None,
            })
            chosen_core_sigs.add(cand.core_signature)
            chosen_item_sets.add(cand_item_sig)
            if len(selected_looks) >= body.limit:
                break

    # Shortfall is requested count minus distinct wardrobe looks meeting the quality threshold
    shortfall = max(0, body.limit - len(selected_looks))

    # 9. Catalog completion to fill shortfall (if allowed)
    budget_cents = int(body.budget_max * 100) if body.budget_max is not None and body.budget_max > 0 else None
    budget_status: Optional[str] = None
    no_products_in_budget = False
    cheapest_alt: Optional[dict[str, Any]] = None
    above_threshold_mixed: list[tuple[float, OutfitCandidate, dict[str, float], list[str], dict[str, Any]]] = []
    below_threshold_mixed: list[tuple[float, OutfitCandidate, dict[str, float], list[str], dict[str, Any]]] = []

    if shortfall > 0 and effective_allow_catalog:
        try:
            products_res = (
                client.from_("products")
                .select("*")
                .in_("audience", ["unisex", "all"])
                .execute()
            )
            all_catalog_products = products_res.data or []
        except Exception as exc:
            logger.warning(f"Could not load catalog products for completion: {exc}")
            all_catalog_products = []

        # Strict audience filter: only 'unisex' or 'all' (never infer audience from image/name/body_shape)
        eligible_products = [
            p for p in all_catalog_products
            if _is_valid_uuid(p.get("id"))
            and str(p.get("audience", "all")).strip().lower() in ("unisex", "all")
        ]

        # Filter products matching occasion and season (Option 1: strict evidence policy)
        matching_catalog_items = [
            p for p in eligible_products
            if _matches_occasion(p.get("occasions"), occasion)
            and _matches_season(p.get("seasons"), season)
        ]
        matching_catalog_items.sort(key=lambda p: int(p.get("price_cents") or 0))

        if budget_cents is not None:
            in_budget_items = [p for p in matching_catalog_items if int(p.get("price_cents") or 0) <= budget_cents]
            if in_budget_items:
                candidate_products = in_budget_items[:30]
                budget_status = "within_budget"
            elif matching_catalog_items:
                no_products_in_budget = True
                budget_status = "no_products_in_budget"
                cheapest_alt = _to_catalog_suggestion(matching_catalog_items[0]).model_dump()
                candidate_products = []
            else:
                candidate_products = []
                budget_status = "no_products_found"
        else:
            candidate_products = matching_catalog_items[:30]
            budget_status = "within_budget" if matching_catalog_items else "no_products_found"

        for prod in candidate_products:
            p_slot = str(prod.get("slot") or prod.get("category", "top")).strip().lower()
            catalog_item_id = f"catalog_{prod['id']}"
            cat_engine_item = {
                "id": catalog_item_id,
                "category": p_slot,
                "slot": p_slot,
                "sub_category": prod.get("subtype") or prod.get("name"),
                "color": (prod.get("color_tags") or ["#111827"])[0],
                "colors": prod.get("color_tags") or [],
                "fit": prod.get("fit", "regular"),
                "formality": prod.get("formality", 1),
                "occasions": prod.get("occasions") or [occasion],
                "seasons": prod.get("seasons") or [],
                "styles": prod.get("style_tags") or [],
                "pattern": prod.get("pattern", "solid"),
                "is_available": True,
                "source_type": "catalog",
            }

            all_skeletons = generate_candidates([*engine_items, cat_engine_item])
            for cand in all_skeletons:
                # Must contain this catalog item
                if catalog_item_id not in cand.item_ids:
                    continue
                # Must contain at least one wardrobe item
                if all(it_id == catalog_item_id for it_id in cand.item_ids):
                    continue
                # Must contain exactly one catalog item
                if sum(1 for it_id in cand.item_ids if it_id.startswith("catalog_")) != 1:
                    continue
                # Hard rules & anti-clash
                if not hard_filter_candidate(cand, occasion, season):
                    continue

                base_score = float(score_outfit(cand, occasion=occasion, season=season, body_shape=body_shape, attrs=attrs))
                affinity_delta, _ = compute_outfit_affinity_adjustment(cand, affinities) if affinities else (0.0, [])
                total_score = round(max(0.0, min(1.0, base_score + affinity_delta)), 3)

                scores = feature_scores(cand, occasion=occasion, season=season, body_shape=body_shape, attrs=attrs)
                if affinities and affinities.get("total_events"):
                    scores["style_dna"] = round(max(0.0, min(1.0, 0.5 + (affinity_delta / 0.16))), 3)

                reasons = explain_outfit(
                    cand,
                    occasion=occasion,
                    season=season,
                    body_shape=body_shape,
                    attrs=attrs,
                    affinities=affinities,
                )
                reasons.append(f"Completed look adding {prod.get('name', 'catalog product')} to complete the {p_slot} slot.")

                item_payload = (total_score, cand, scores, reasons, prod)
                if total_score >= body.min_quality_threshold:
                    above_threshold_mixed.append(item_payload)
                else:
                    below_threshold_mixed.append(item_payload)

        # Sort candidate pools by score descending, then stable core signature
        sort_key = lambda item: (
            round(-item[0], 4),
            tuple(sorted(item[1].core_signature)),
            item[1].item_ids,
        )
        above_threshold_mixed.sort(key=sort_key)
        below_threshold_mixed.sort(key=sort_key)

        # Fill shortfall with above-threshold mixed looks:
        # Pass 1: Prioritize distinct core combinations not yet present in chosen_core_sigs
        for total_score, cand, scores, reasons, prod in above_threshold_mixed:
            cand_item_sig = tuple(sorted(cand.item_ids))
            if cand_item_sig in chosen_item_sets:
                continue
            if body.is_shuffle and cand.core_signature in exclude_cores:
                continue
            if cand.core_signature in chosen_core_sigs:
                continue

            selected_looks.append({
                "candidate": cand,
                "score": total_score,
                "scores": scores,
                "reasons": reasons,
                "source_type": "mixed",
                "is_below_threshold": False,
                "quality_warning": None,
                "catalog_product": prod,
            })
            chosen_core_sigs.add(cand.core_signature)
            chosen_item_sets.add(cand_item_sig)
            shortfall -= 1
            if shortfall == 0:
                break

        # Pass 2: If shortfall remains (e.g. sparse wardrobe where no more distinct cores exist),
        # permit reusing an existing core if it is completed with a distinct item (different catalog piece)
        if shortfall > 0:
            for total_score, cand, scores, reasons, prod in above_threshold_mixed:
                cand_item_sig = tuple(sorted(cand.item_ids))
                if cand_item_sig in chosen_item_sets:
                    continue
                if body.is_shuffle and cand.core_signature in exclude_cores:
                    continue

                selected_looks.append({
                    "candidate": cand,
                    "score": total_score,
                    "scores": scores,
                    "reasons": reasons,
                    "source_type": "mixed",
                    "is_below_threshold": False,
                    "quality_warning": None,
                    "catalog_product": prod,
                })
                chosen_core_sigs.add(cand.core_signature)
                chosen_item_sets.add(cand_item_sig)
                shortfall -= 1
                if shortfall == 0:
                    break

    # 10. Fall back to below-threshold unique looks (wardrobe first, then mixed) if shortfall remains
    below_threshold_included = 0
    if shortfall > 0 and (below_threshold_wardrobe or below_threshold_mixed):
        # 10a. Wardrobe below-threshold looks: Pass 1 distinct cores, Pass 2 peripheral variations
        for total_score, cand, scores, reasons in below_threshold_wardrobe:
            cand_item_sig = tuple(sorted(cand.item_ids))
            if cand_item_sig in chosen_item_sets:
                continue
            if body.is_shuffle and cand.core_signature in exclude_cores:
                continue
            if cand.core_signature in chosen_core_sigs:
                continue
            quality_warn = (
                f"Compatibility score {total_score:.2f} is below your preferred quality threshold "
                f"({body.min_quality_threshold:.2f}); included as a last-resort alternative."
            )
            selected_looks.append({
                "candidate": cand,
                "score": total_score,
                "scores": scores,
                "reasons": reasons,
                "source_type": "wardrobe",
                "is_below_threshold": True,
                "quality_warning": quality_warn,
                "catalog_product": None,
            })
            chosen_core_sigs.add(cand.core_signature)
            chosen_item_sets.add(cand_item_sig)
            below_threshold_included += 1
            shortfall -= 1
            if shortfall == 0:
                break

        if shortfall > 0:
            for total_score, cand, scores, reasons in below_threshold_wardrobe:
                cand_item_sig = tuple(sorted(cand.item_ids))
                if cand_item_sig in chosen_item_sets:
                    continue
                if body.is_shuffle and cand.core_signature in exclude_cores:
                    continue
                quality_warn = (
                    f"Compatibility score {total_score:.2f} is below your preferred quality threshold "
                    f"({body.min_quality_threshold:.2f}); included as a last-resort alternative."
                )
                selected_looks.append({
                    "candidate": cand,
                    "score": total_score,
                    "scores": scores,
                    "reasons": reasons,
                    "source_type": "wardrobe",
                    "is_below_threshold": True,
                    "quality_warning": quality_warn,
                    "catalog_product": None,
                })
                chosen_core_sigs.add(cand.core_signature)
                chosen_item_sets.add(cand_item_sig)
                below_threshold_included += 1
                shortfall -= 1
                if shortfall == 0:
                    break

        # 10b. Mixed below-threshold looks: Pass 1 distinct cores, Pass 2 peripheral variations
        if shortfall > 0:
            for total_score, cand, scores, reasons, prod in below_threshold_mixed:
                cand_item_sig = tuple(sorted(cand.item_ids))
                if cand_item_sig in chosen_item_sets:
                    continue
                if body.is_shuffle and cand.core_signature in exclude_cores:
                    continue
                if cand.core_signature in chosen_core_sigs:
                    continue
                quality_warn = (
                    f"Compatibility score {total_score:.2f} is below your preferred quality threshold "
                    f"({body.min_quality_threshold:.2f}); completed with store piece as an alternative."
                )
                selected_looks.append({
                    "candidate": cand,
                    "score": total_score,
                    "scores": scores,
                    "reasons": reasons,
                    "source_type": "mixed",
                    "is_below_threshold": True,
                    "quality_warning": quality_warn,
                    "catalog_product": prod,
                })
                chosen_core_sigs.add(cand.core_signature)
                chosen_item_sets.add(cand_item_sig)
                below_threshold_included += 1
                shortfall -= 1
                if shortfall == 0:
                    break

        if shortfall > 0:
            for total_score, cand, scores, reasons, prod in below_threshold_mixed:
                cand_item_sig = tuple(sorted(cand.item_ids))
                if cand_item_sig in chosen_item_sets:
                    continue
                if body.is_shuffle and cand.core_signature in exclude_cores:
                    continue
                quality_warn = (
                    f"Compatibility score {total_score:.2f} is below your preferred quality threshold "
                    f"({body.min_quality_threshold:.2f}); completed with store piece as an alternative."
                )
                selected_looks.append({
                    "candidate": cand,
                    "score": total_score,
                    "scores": scores,
                    "reasons": reasons,
                    "source_type": "mixed",
                    "is_below_threshold": True,
                    "quality_warning": quality_warn,
                    "catalog_product": prod,
                })
                chosen_core_sigs.add(cand.core_signature)
                chosen_item_sets.add(cand_item_sig)
                below_threshold_included += 1
                shortfall -= 1
                if shortfall == 0:
                    break

    # If no looks at all could be matched, return structured empty state
    if not selected_looks:
        if body.is_shuffle and exclude_cores:
            return GenerateOutfitsResponse(
                outfits=[],
                status="no_matching_combinations",
                message=f"No further unseen combinations could be created from your rack for '{body.occasion}'. All valid looks have been shown.",
                missing_slots=[],
                profile_warning=profile_warning,
                budget_status=budget_status,
                no_products_in_budget=no_products_in_budget,
                cheapest_alternative=cheapest_alt,
            )
        status_val = "missing_required_slots" if critical_missing else "no_matching_combinations"
        if no_products_in_budget:
            msg_val = "No catalog products within your budget could complete an outfit. Consider the cheapest alternative."
        elif critical_missing and effective_allow_catalog:
            msg_val = "Your wardrobe is missing required items for this occasion, and no eligible store pieces could complete a look."
        elif critical_missing:
            msg_val = "Your wardrobe is missing required items to build outfits for this occasion."
        else:
            msg_val = f"No suitable outfits could be matched for '{body.occasion}'. Try adjusting the occasion or adding versatile pieces."

        return GenerateOutfitsResponse(
            outfits=[],
            status=status_val,
            message=msg_val,
            missing_slots=critical_missing,
            profile_warning=profile_warning,
            budget_status=budget_status,
            no_products_in_budget=no_products_in_budget,
            cheapest_alternative=cheapest_alt,
        )

    # 11. Persist outfits atomically and build responses
    now_iso = datetime.now(timezone.utc).isoformat()
    persisted_outfits: list[OutfitResponse] = []

    for look in selected_looks:
        outfit_id = str(uuid4())
        cand = look["candidate"]
        total_score = look["score"]
        scores = look["scores"]
        reasons = look["reasons"]
        is_mixed = look["source_type"] == "mixed"
        prod = look["catalog_product"]
        is_below = look["is_below_threshold"]
        q_warn = look["quality_warning"]

        slot_items: list[OutfitSlotItem] = []
        item_insert_rows: list[dict[str, Any]] = []

        for slot_name, item_dict in cand.slots.items():
            raw_id = str(item_dict.get("id", ""))
            if is_mixed and prod and raw_id == f"catalog_{prod['id']}":
                slot_item = _format_slot_item(prod, slot_name, client, source_type="catalog", product=prod)
                slot_items.append(slot_item)
                item_insert_rows.append({
                    "outfit_id": outfit_id,
                    "user_id": user.id,
                    "slot": slot_name,
                    "source_type": "catalog",
                    "wardrobe_item_id": None,
                    "product_id": str(prod["id"]),
                    "created_at": now_iso,
                })
            else:
                raw_meta = item_by_id.get(raw_id, item_dict)
                slot_item = _format_slot_item(raw_meta, slot_name, client, source_type="wardrobe")
                slot_items.append(slot_item)
                item_insert_rows.append({
                    "outfit_id": outfit_id,
                    "user_id": user.id,
                    "slot": slot_name,
                    "source_type": "wardrobe",
                    "wardrobe_item_id": raw_id,
                    "product_id": None,
                    "created_at": now_iso,
                })

        metadata_payload: dict[str, Any] = {}
        if is_mixed and prod:
            metadata_payload["fallback_reason"] = "shortfall_catalog_completion"
            metadata_payload["unlocked_by_product_id"] = str(prod["id"])
        if is_below:
            metadata_payload["quality_warning"] = q_warn

        outfit_row = {
            "id": outfit_id,
            "user_id": user.id,
            "occasion": occasion,
            "vibe": body.vibe or "casual",
            "skeleton": cand.skeleton,
            "score": round(float(total_score), 3),
            "component_scores": {k: round(float(v), 3) for k, v in scores.items()},
            "reasons": reasons,
            "wardrobe_only": not is_mixed,
            "is_saved": False,
            "metadata": metadata_payload,
            "created_at": now_iso,
            "updated_at": now_iso,
        }

        # Atomic persistence check: never return an outfit if database insert fails
        persisted = _persist_outfit_and_items(client, outfit_row, item_insert_rows)
        if not persisted:
            logger.error(f"Persistence failed for outfit {outfit_id}; skipping from response.")
            continue

        ai_summary = None
        if len(persisted_outfits) == 0:
            ai_summary = await _rephrase_explanation_with_openrouter(
                items=slot_items,
                reasons=reasons,
                occasion=occasion,
                vibe=body.vibe,
            )

        shoes_included = "shoes" in cand.slots
        formalities: list[int] = []
        for item in cand.slots.values():
            val = item.get("formality") if isinstance(item, dict) else getattr(item, "formality", 1)
            try:
                formalities.append(int(val) if val is not None else 1)
            except (ValueError, TypeError):
                formalities.append(1)
        formality_spread = (max(formalities) - min(formalities)) if len(formalities) >= 2 else 0

        persisted_outfits.append(
            OutfitResponse(
                id=outfit_id,
                user_id=user.id,
                occasion=occasion,
                vibe=body.vibe,
                vibes=body.vibes if body.vibes else ([body.vibe] if body.vibe else None),
                season=season,
                shoes_included=shoes_included,
                formality_spread=formality_spread,
                core_type=classify_outfit_core(cand),
                skeleton=cand.skeleton,
                score=round(float(total_score), 3),
                component_scores={k: round(float(v), 3) for k, v in scores.items()},
                reasons=reasons,
                ai_summary=ai_summary,
                wardrobe_only=not is_mixed,
                fallback_reason="shortfall_catalog_completion" if is_mixed else None,
                unlocked_by_product_id=str(prod["id"]) if is_mixed and prod else None,
                is_saved=False,
                is_below_threshold=is_below,
                quality_warning=q_warn,
                core_signature=sorted(list(cand.core_signature)),
                items=slot_items,
                created_at=now_iso,
            )
        )

    # If all persistence attempts failed, surface database error
    if selected_looks and not persisted_outfits:
        raise AppException(
            message=(
                "Database persistence failed for all generated recommendations. "
                "Ensure save_outfit_with_items RPC migration has been applied."
            ),
            code="OUTFIT_PERSISTENCE_ERROR",
            status_code=500,
        )

    # 12. Determine status and messages
    status_val = "partial_results" if len(persisted_outfits) < body.limit else "success"

    message = None
    if status_val == "partial_results":
        if body.is_shuffle and exclude_cores:
            message = f"Found {len(persisted_outfits)} alternative outfit(s) for '{occasion}'. No further unseen combinations remain on your rack."
        elif no_products_in_budget:
            message = f"Found {len(persisted_outfits)} of {body.limit} requested outfit(s). No further catalog products within your budget could complete an outfit."
        elif any(not o.wardrobe_only for o in persisted_outfits):
            message = f"Found {len(persisted_outfits)} of {body.limit} requested outfit(s) for '{occasion}', completed with store pieces. All valid combinations have been shown."
        else:
            message = f"Found {len(persisted_outfits)} of {body.limit} requested unique outfit(s) for '{occasion}'. All valid combinations from your rack have been shown."
    elif no_products_in_budget:
        message = "No catalog products within your budget could complete an outfit. Consider the cheapest alternative."
    elif any(not o.wardrobe_only for o in persisted_outfits) and any(o.wardrobe_only for o in persisted_outfits):
        message = "Showing your wardrobe outfits followed by recommended mixed looks."
    elif any(not o.wardrobe_only for o in persisted_outfits):
        message = "Showing outfits completed with catalog items."

    quality_warning_summary = None
    if below_threshold_included > 0:
        quality_warning_summary = (
            f"{below_threshold_included} outfit(s) fall below the {body.min_quality_threshold:.2f} quality threshold "
            f"due to limited high-compatibility pieces in your wardrobe."
        )

    return GenerateOutfitsResponse(
        outfits=persisted_outfits,
        status=status_val,
        message=message,
        missing_slots=[],
        profile_warning=profile_warning,
        quality_warning=quality_warning_summary,
        budget_status=budget_status,
        no_products_in_budget=no_products_in_budget,
        cheapest_alternative=cheapest_alt,
    )


# ==============================================================================
# Saved Looks & Mutation Endpoints
# ==============================================================================


@router.get(
    "/saved",
    response_model=SavedOutfitsListResponse,
    summary="Get caller's saved looks, optionally filtered by tag",
)
async def list_saved_outfits(
    tag: Optional[str] = Query(None, description="Optional tag filter (e.g. Work, Date Night, Wedding, Vacation, Try Later)"),
    token: str = Depends(get_current_token),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Retrieves all outfits bookmarked/saved by the caller with populated items, optionally filtered by tag."""
    client = get_user_scoped_supabase_client(token)

    canonical_tag = None
    if tag is not None:
        clean_tag = " ".join(tag.strip().split())
        if not clean_tag:
            raise AppException(
                message=f"Empty tag filter is not permitted. Approved tags are: {', '.join(APPROVED_OUTFIT_TAGS)}.",
                code="INVALID_TAG",
                status_code=422,
            )
        canonical_tag = APPROVED_OUTFIT_TAGS_MAP.get(clean_tag.lower())
        if not canonical_tag:
            raise AppException(
                message=f"Unsupported tag filter '{tag}'. Approved tags are: {', '.join(APPROVED_OUTFIT_TAGS)}.",
                code="INVALID_TAG",
                status_code=422,
            )

    try:
        query = (
            client.from_("outfits")
            .select("*")
            .eq("user_id", user.id)
            .eq("is_saved", True)
            .order("updated_at", desc=True)
        )
        if canonical_tag:
            query = query.contains("tags", [canonical_tag])
        outfits_res = query.execute()
    except Exception as exc:
        if isinstance(exc, AppException):
            raise exc
        logger.error(f"Failed to fetch saved outfits for user {user.id}: {exc}")
        raise AppException(
            message="Unable to retrieve saved outfits.",
            code="SAVED_OUTFITS_FETCH_ERROR",
            status_code=500,
        )

    outfit_rows = outfits_res.data or []
    if not outfit_rows:
        return SavedOutfitsListResponse(outfits=[], total=0, available_tags=[])

    outfit_ids = [r["id"] for r in outfit_rows]

    # Fetch all item references for these outfits (supporting wardrobe items and products)
    try:
        items_res = (
            client.from_("outfit_items")
            .select("*, wardrobe_items(*), products(*)")
            .in_("outfit_id", outfit_ids)
            .execute()
        )
    except Exception as exc:
        logger.warning(f"Failed to fetch outfit_items: {exc}")
        items_res = None

    items_by_outfit: dict[str, list[OutfitSlotItem]] = {}
    if items_res and items_res.data:
        for it in items_res.data:
            outfit_id = it.get("outfit_id")
            source_type = it.get("source_type", "wardrobe")
            slot_name = it.get("slot", "item")
            if source_type == "catalog":
                prod = it.get("products") or {}
                formatted = _format_slot_item(prod, slot_name, client, source_type="catalog", product=prod)
            else:
                w_item = it.get("wardrobe_items") or {}
                formatted = _format_slot_item(w_item, slot_name, client, source_type="wardrobe")
            items_by_outfit.setdefault(outfit_id, []).append(formatted)

    results: list[OutfitResponse] = []
    user_tags: set[str] = set()

    for r in outfit_rows:
        o_id = r["id"]
        meta = r.get("metadata") or {}
        row_tags = r.get("tags") or []
        for t in row_tags:
            user_tags.add(t)
        o_items = items_by_outfit.get(o_id, [])
        saved_core_sig: list[tuple[str, str]] = sorted([
            (it.slot, str(it.wardrobe_item_id or it.product_id or ""))
            for it in o_items
            if it.slot in CORE_SLOTS and (it.wardrobe_item_id or it.product_id)
        ])
        results.append(
            OutfitResponse(
                id=o_id,
                user_id=str(r.get("user_id")),
                occasion=r.get("occasion", "casual"),
                vibe=r.get("vibe"),
                skeleton=r.get("skeleton", "top_bottom"),
                score=float(r.get("score", 0.5)),
                component_scores=r.get("component_scores") or {},
                reasons=r.get("reasons") or [],
                wardrobe_only=bool(r.get("wardrobe_only", True)),
                fallback_reason=meta.get("fallback_reason"),
                unlocked_by_product_id=meta.get("unlocked_by_product_id"),
                is_saved=True,
                tags=row_tags,
                core_signature=saved_core_sig,
                items=o_items,
                created_at=str(r.get("created_at", "")),
            )
        )

    return SavedOutfitsListResponse(
        outfits=results,
        total=len(results),
        available_tags=sorted(list(user_tags)),
    )


def _extract_outfit_event_metadata(
    client: Any,
    outfit_id: str,
    outfit_row: dict[str, Any],
    extra_metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Extracts styling attributes from outfit_items for Style DNA affinity learning.

    Covers both wardrobe items and catalog products without fabricating wardrobe attributes.
    """
    colors: set[str] = set()
    categories: set[str] = set()
    styles: set[str] = set()

    def _collect(target: set[str], val: Any) -> None:
        if not val:
            return
        if isinstance(val, (list, tuple, set)):
            for v in val:
                if v:
                    target.add(str(v).strip().lower())
        else:
            target.add(str(val).strip().lower())

    try:
        items_res = (
            client.from_("outfit_items")
            .select(
                "slot, source_type, wardrobe_items(category, slot, sub_category, primary_color, color_tags, style_tags), products(category, slot, subtype, color_tags, colors, style_tags)"
            )
            .eq("outfit_id", outfit_id)
            .execute()
        )
        for row in (items_res.data or []):
            _collect(categories, row.get("slot"))

            # 1. Wardrobe items
            w_item = row.get("wardrobe_items") or {}
            _collect(categories, w_item.get("category"))
            _collect(categories, w_item.get("sub_category"))
            _collect(colors, w_item.get("primary_color"))
            _collect(colors, w_item.get("color_tags"))
            _collect(styles, w_item.get("style_tags"))

            # 2. Catalog products (without fabricating wardrobe attributes)
            p_item = row.get("products") or {}
            _collect(categories, p_item.get("category"))
            _collect(categories, p_item.get("slot"))
            _collect(categories, p_item.get("subtype"))
            _collect(colors, p_item.get("color_tags"))
            _collect(colors, p_item.get("colors"))
            _collect(styles, p_item.get("style_tags"))
    except Exception as exc:
        logger.debug(f"Could not load items for event metadata: {exc}")

    metadata = {
        "colors": sorted(list(colors)),
        "categories": sorted(list(categories)),
        "styles": sorted(list(styles)),
        "occasion": outfit_row.get("occasion"),
    }
    if extra_metadata:
        metadata.update(extra_metadata)
    return metadata


@router.post(
    "/{outfit_id}/save",
    response_model=SaveOutfitResponse,
    summary="Save / bookmark an outfit look for later with optional tags",
)
async def save_outfit(
    outfit_id: str,
    body: Optional[SaveOutfitRequest] = None,
    token: str = Depends(get_current_token),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Marks an outfit as saved for later with optional tags.

    - Normalizes tags to approved canonical set, defaulting to ['Try Later'].
    - Atomicity & Consistency:
      Calls `save_outfit_with_event` PostgreSQL RPC to atomically update the
      outfit's saved status/tags and record the Style DNA save event in a single
      ACID transaction with row-level locking (SELECT ... FOR UPDATE) to serialize
      concurrent saves and enforce uniqueness.
      Refuses non-atomic fallbacks to guarantee that outfit saved status and
      Style DNA interaction events can never diverge.
    - Idempotency: Repeated saves or retagging on an already-saved look update tags
      without creating duplicate outfit_events save interactions.
    """
    client = get_user_scoped_supabase_client(token)
    tags = normalize_outfit_tags(body.tags if body else None)

    # 1. Verify outfit exists and belongs to caller
    try:
        outfit_res = (
            client.from_("outfits")
            .select("id, user_id, occasion, vibe, skeleton, is_saved, tags")
            .eq("id", outfit_id)
            .eq("user_id", user.id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.error(f"Failed to query outfit {outfit_id} for save: {exc}")
        raise AppException(message="Unable to verify outfit.", code="SAVE_ERROR", status_code=500)

    if not outfit_res.data:
        raise AppException(message="Outfit not found or unauthorized.", code="NOT_FOUND", status_code=404)

    outfit_row = outfit_res.data[0]

    # Extract item attributes for transparent Style DNA derivation (wardrobe + catalog)
    event_metadata = _extract_outfit_event_metadata(
        client=client,
        outfit_id=outfit_id,
        outfit_row=outfit_row,
        extra_metadata={"tags": tags},
    )

    # Execute atomic PostgreSQL RPC under ACID transaction
    try:
        rpc_res = client.rpc(
            "save_outfit_with_event",
            {
                "p_outfit_id": outfit_id,
                "p_tags": tags,
                "p_event_metadata": event_metadata,
            },
        ).execute()
        if rpc_res and getattr(rpc_res, "data", None):
            return SaveOutfitResponse(
                success=True,
                message="Outfit saved for later.",
                is_saved=True,
                tags=tags,
            )
        logger.error(
            f"Atomic save RPC save_outfit_with_event returned empty data for outfit {outfit_id}. "
            "Refusing non-atomic fallback."
        )
        raise AppException(message="Unable to save outfit.", code="SAVE_ERROR", status_code=500)
    except AppException:
        raise
    except Exception as rpc_exc:
        err_msg = str(rpc_exc)
        if "OUTFIT_NOT_FOUND" in err_msg:
            raise AppException(message="Outfit not found or unauthorized.", code="NOT_FOUND", status_code=404)
        logger.error(
            f"Atomic save via save_outfit_with_event failed for outfit {outfit_id}: {rpc_exc}. "
            "Refusing non-atomic fallback to guarantee consistent Style DNA tracking. "
            "Deployment requirement: verify scripts/migrations/2026-10-21_save_outfit_and_event_rpc.sql is applied."
        )
        raise AppException(message="Unable to save outfit.", code="SAVE_ERROR", status_code=500)


@router.put(
    "/{outfit_id}/tags",
    summary="Update tags on an already-saved outfit",
)
async def update_outfit_tags(
    outfit_id: str,
    body: UpdateOutfitTagsRequest,
    token: str = Depends(get_current_token),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Updates classification tags for an existing saved outfit."""
    client = get_user_scoped_supabase_client(token)
    now_iso = datetime.now(timezone.utc).isoformat()
    tags = validate_and_normalize_tags(body.tags, allow_default=False)

    try:
        res = (
            client.from_("outfits")
            .update({"tags": tags, "updated_at": now_iso})
            .eq("id", outfit_id)
            .eq("user_id", user.id)
            .eq("is_saved", True)
            .execute()
        )
    except Exception as exc:
        logger.error(f"Failed to update tags for outfit {outfit_id}: {exc}")
        raise AppException(message="Unable to update outfit tags.", code="TAG_UPDATE_ERROR", status_code=500)

    if not res.data:
        raise AppException(
            message="Saved outfit not found or unauthorized.",
            code="NOT_FOUND",
            status_code=404,
        )

    return {"success": True, "tags": tags}


@router.delete(
    "/{outfit_id}/save",
    summary="Unsave an outfit look",
)
async def unsave_outfit(
    outfit_id: str,
    token: str = Depends(get_current_token),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Removes an outfit from saved/bookmarked status and clears its tags."""
    client = get_user_scoped_supabase_client(token)
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        res = (
            client.from_("outfits")
            .update({"is_saved": False, "tags": [], "updated_at": now_iso})
            .eq("id", outfit_id)
            .eq("user_id", user.id)
            .execute()
        )
    except Exception as exc:
        raise AppException(message="Unable to unsave outfit.", code="UNSAVE_ERROR", status_code=500)

    if not res.data:
        raise AppException(message="Outfit not found or unauthorized.", code="NOT_FOUND", status_code=404)

    return {"success": True, "message": "Outfit removed from saved looks."}


@router.get(
    "/{outfit_id}",
    response_model=OutfitResponse,
    summary="Get single outfit details",
)
async def get_outfit_details(
    outfit_id: str,
    token: str = Depends(get_current_token),
    user: AuthenticatedUser = Depends(get_current_user),
):
    client = get_user_scoped_supabase_client(token)

    try:
        outfit_res = (
            client.from_("outfits")
            .select("*")
            .eq("id", outfit_id)
            .eq("user_id", user.id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise AppException(message=f"Failed to get outfit: {exc}", code="QUERY_ERROR", status_code=500)

    if not outfit_res.data:
        raise AppException(message="Outfit not found.", code="NOT_FOUND", status_code=404)

    row = outfit_res.data[0]

    # Fetch items
    items_res = (
        client.from_("outfit_items")
        .select("*, wardrobe_items(*)")
        .eq("outfit_id", outfit_id)
        .execute()
    )

    slot_items = []
    for it in (items_res.data or []):
        w_item = it.get("wardrobe_items") or {}
        slot_name = it.get("slot", "item")
        slot_items.append(_format_slot_item(w_item, slot_name, client))

    return OutfitResponse(
        id=outfit_id,
        user_id=str(row["user_id"]),
        occasion=row.get("occasion", "casual"),
        vibe=row.get("vibe"),
        skeleton=row.get("skeleton", "top_bottom"),
        score=float(row.get("score", 0.5)),
        component_scores=row.get("component_scores") or {},
        reasons=row.get("reasons") or [],
        wardrobe_only=bool(row.get("wardrobe_only", True)),
        is_saved=bool(row.get("is_saved", False)),
        items=slot_items,
        created_at=str(row.get("created_at", "")),
    )


# ==============================================================================
# Outfit Events & Feedback Endpoints
# ==============================================================================


@router.post(
    "/{outfit_id}/events",
    response_model=OutfitEventResponse,
    summary="Record like, dislike, save, skip, or wear event on an outfit",
)
async def record_outfit_event(
    outfit_id: str,
    body: RecordOutfitEventRequest,
    token: str = Depends(get_current_token),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Record an interaction event (like, dislike, save, skip, wear) on an outfit.

    Strictly verifies that the referenced outfit belongs to the authenticated caller.
    """
    client = get_user_scoped_supabase_client(token)

    # 1. Verify referenced outfit belongs to caller
    try:
        outfit_res = (
            client.from_("outfits")
            .select("id, user_id, occasion, vibe, skeleton")
            .eq("id", outfit_id)
            .eq("user_id", user.id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.error(f"Failed to verify outfit {outfit_id} ownership: {exc}")
        raise AppException(
            message="Failed to verify outfit ownership.",
            code="OUTFIT_VERIFY_ERROR",
            status_code=500,
        )

    if not outfit_res.data:
        raise AppException(
            message="Outfit not found or access denied.",
            code="OUTFIT_NOT_FOUND",
            status_code=404,
        )

    outfit_row = outfit_res.data[0]

    # Idempotency check for direct 'save' events to avoid duplicate Style DNA records
    if body.event_type == "save":
        try:
            existing_event = (
                client.from_("outfit_events")
                .select("id, user_id, outfit_id, event_type, metadata, created_at")
                .eq("user_id", user.id)
                .eq("outfit_id", outfit_id)
                .eq("event_type", "save")
                .limit(1)
                .execute()
            )
            if existing_event.data:
                ev = existing_event.data[0]
                now_iso = datetime.now(timezone.utc).isoformat()
                try:
                    client.from_("outfits").update({"is_saved": True, "updated_at": now_iso}).eq("id", outfit_id).execute()
                except Exception:
                    pass
                return OutfitEventResponse(
                    id=ev["id"],
                    user_id=ev["user_id"],
                    outfit_id=ev["outfit_id"],
                    event_type=ev["event_type"],
                    metadata=ev.get("metadata") or {},
                    created_at=ev.get("created_at") or now_iso,
                )
        except Exception as exc:
            logger.debug(f"Could not check existing save event: {exc}")

    # 2. Extract item attributes for transparent Style DNA derivation (wardrobe + catalog)
    event_metadata = _extract_outfit_event_metadata(
        client=client,
        outfit_id=outfit_id,
        outfit_row=outfit_row,
        extra_metadata=body.metadata,
    )

    event_id = str(uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()
    event_row = {
        "id": event_id,
        "user_id": user.id,
        "outfit_id": outfit_id,
        "event_type": body.event_type,
        "metadata": event_metadata,
        "created_at": now_iso,
    }

    try:
        client.from_("outfit_events").insert(event_row).execute()
    except Exception as exc:
        logger.error(f"Failed to record event for outfit {outfit_id}: {exc}")
        raise AppException(
            message="Failed to record outfit event.",
            code="EVENT_INSERT_ERROR",
            status_code=500,
        )

    # Sync is_saved state
    if body.event_type in ("save", "like"):
        try:
            current_tags = outfit_row.get("tags") or ["Try Later"]
            client.from_("outfits").update({"is_saved": True, "tags": current_tags, "updated_at": now_iso}).eq("id", outfit_id).execute()
        except Exception:
            pass
    elif body.event_type == "dislike":
        try:
            client.from_("outfits").update({"is_saved": False, "tags": [], "updated_at": now_iso}).eq("id", outfit_id).execute()
        except Exception:
            pass

    return OutfitEventResponse(
        id=event_id,
        user_id=user.id,
        outfit_id=outfit_id,
        event_type=body.event_type,
        metadata=event_row["metadata"],
        created_at=now_iso,
    )
