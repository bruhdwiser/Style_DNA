"""Outfit generation and saved looks router.

Uses the pure Python rules engine to generate, score, diversify, explain,
and persist outfits and their item references.
All data access uses the authenticated user's client (preserving RLS).
"""

from __future__ import annotations

import logging
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
)
from ..schemas.style_dna import RecordOutfitEventRequest, OutfitEventResponse
from ..schemas.user import AuthenticatedUser
from ..styling.explain import explain_outfit
from ..styling.features import feature_scores, score_outfit
from ..styling.gaps import rank_gaps
from ..styling.generator import generate_outfits
from ..styling.learning import calculate_affinities, compute_outfit_affinity_adjustment
from ..styling.taxonomy import calculate_slot_coverage
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
                    "X-Title": "FlashFit Fashion AI",
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
    - Empty wardrobe or missing required slots returns a structured empty state.
    - Wardrobe-only mode strictly excludes catalog items.
    - Persists generated outfits and item mappings in PostgreSQL.
    """
    client = get_user_scoped_supabase_client(token)

    # 1. Fetch caller's wardrobe items (enforced by RLS)
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

    # 2. Check for empty wardrobe
    if not wardrobe_items:
        return GenerateOutfitsResponse(
            outfits=[],
            status="empty_wardrobe",
            message="Your wardrobe is empty. Add clothing items to your closet before generating outfits.",
            missing_slots=["top", "bottom", "shoes"],
        )

    # 3. Check for missing critical slots and fallback applicability
    coverage = calculate_slot_coverage(wardrobe_items)
    critical_missing = coverage.get("critical_missing") or []

    fallback_triggered = False
    fallback_reason: Optional[str] = None
    fallback_slot: Optional[str] = None

    if not coverage.get("is_ready_for_outfits") and critical_missing:
        # If user did not opt into catalog fallback or explicitly asked for wardrobe_only:
        if body.wardrobe_only or not body.allow_one_new_item:
            return GenerateOutfitsResponse(
                outfits=[],
                status="missing_required_slots",
                message="Your wardrobe is missing required items to build outfits for this occasion.",
                missing_slots=critical_missing,
            )
        # Opted in to allow_one_new_item and wardrobe_only is False:
        fallback_triggered = True
        fallback_slot = critical_missing[0]
        fallback_reason = f"missing_required_slot: {fallback_slot}"

    # 4. Fetch caller's style profile (optional preferences)
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

    # 7. Generate wardrobe-only outfits first (if wardrobe is ready)
    occasion = body.occasion.strip().lower()
    season = body.season.strip().lower()

    wardrobe_candidates = []
    if coverage.get("is_ready_for_outfits"):
        wardrobe_candidates = generate_outfits(
            engine_items,
            occasion=occasion,
            season=season,
            body_shape=body_shape,
            attrs=attrs,
            affinities=affinities,
            limit=body.limit,
        )

    # Check score threshold for wardrobe candidates
    good_wardrobe_candidates = [
        c
        for c in wardrobe_candidates
        if float(score_outfit(c, occasion=occasion, season=season, body_shape=body_shape, attrs=attrs))
        >= body.min_quality_threshold
    ]

    # Evaluate fallback if opted-in and too few good outfits
    if not fallback_triggered and body.allow_one_new_item and not body.wardrobe_only:
        if len(wardrobe_candidates) == 0 or len(good_wardrobe_candidates) < min(3, body.limit):
            fallback_triggered = True
            fallback_reason = "insufficient_outfits_above_threshold" if wardrobe_candidates else "no_matching_combinations"
            ranked = rank_gaps(engine_items, occasions=[occasion])
            fallback_slot = ranked[0]["category"] if ranked else "top"

    # If no wardrobe candidates and fallback not triggered, return structured empty state
    if not wardrobe_candidates and not fallback_triggered:
        return GenerateOutfitsResponse(
            outfits=[],
            status="no_matching_combinations",
            message=f"No suitable outfits could be matched for '{body.occasion}'. Try adjusting the occasion or adding versatile pieces.",
            missing_slots=[],
            profile_warning=profile_warning,
        )

    # 8. Build and persist wardrobe-only outfit responses
    now_iso = datetime.now(timezone.utc).isoformat()
    wardrobe_responses: list[OutfitResponse] = []

    for cand in wardrobe_candidates:
        outfit_id = str(uuid4())
        scores = feature_scores(cand, occasion=occasion, season=season, body_shape=body_shape, attrs=attrs)
        base_score = float(score_outfit(cand, occasion=occasion, season=season, body_shape=body_shape, attrs=attrs))

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

        slot_items: list[OutfitSlotItem] = []
        item_insert_rows: list[dict[str, Any]] = []

        for slot_name, item_dict in cand.slots.items():
            item_id = str(item_dict.get("id", ""))
            raw_meta = item_by_id.get(item_id, item_dict)

            slot_item = _format_slot_item(raw_meta, slot_name, client, source_type="wardrobe")
            slot_items.append(slot_item)

            item_insert_rows.append({
                "outfit_id": outfit_id,
                "user_id": user.id,
                "slot": slot_name,
                "source_type": "wardrobe",
                "wardrobe_item_id": item_id,
                "product_id": None,
                "created_at": now_iso,
            })

        outfit_row = {
            "id": outfit_id,
            "user_id": user.id,
            "occasion": occasion,
            "vibe": body.vibe or "casual",
            "skeleton": cand.skeleton,
            "score": round(float(total_score), 3),
            "component_scores": {k: round(float(v), 3) for k, v in scores.items()},
            "reasons": reasons,
            "wardrobe_only": True,
            "is_saved": False,
            "metadata": {},
            "created_at": now_iso,
            "updated_at": now_iso,
        }

        try:
            client.from_("outfits").insert(outfit_row).execute()
            if item_insert_rows:
                client.from_("outfit_items").insert(item_insert_rows).execute()
        except Exception as exc:
            logger.warning(f"Could not persist wardrobe outfit {outfit_id}: {exc}")

        ai_summary = None
        if len(wardrobe_responses) == 0:
            ai_summary = await _rephrase_explanation_with_openrouter(
                items=slot_items,
                reasons=reasons,
                occasion=occasion,
                vibe=body.vibe,
            )

        wardrobe_responses.append(
            OutfitResponse(
                id=outfit_id,
                user_id=user.id,
                occasion=occasion,
                vibe=body.vibe,
                skeleton=cand.skeleton,
                score=round(float(total_score), 3),
                component_scores={k: round(float(v), 3) for k, v in scores.items()},
                reasons=reasons,
                ai_summary=ai_summary,
                wardrobe_only=True,
                is_saved=False,
                items=slot_items,
                created_at=now_iso,
            )
        )

    # 9. If fallback is triggered, generate mixed looks with up to 1 catalog product
    mixed_responses: list[OutfitResponse] = []
    budget_status: Optional[str] = None
    no_products_in_budget: bool = False
    cheapest_alt: Optional[dict[str, Any]] = None

    if fallback_triggered and fallback_slot:
        try:
            products_res = client.from_("products").select("*").execute()
            all_catalog_products = products_res.data or []
        except Exception as exc:
            logger.warning(f"Could not load catalog products for fallback: {exc}")
            all_catalog_products = []

        eligible_products = [
            p
            for p in all_catalog_products
            if _is_valid_uuid(p.get("id")) and _matches_audience(p.get("audience"))
        ]

        matching_catalog_items = [
            p
            for p in eligible_products
            if _matches_slot(p.get("slot"), p.get("category"), fallback_slot)
            and _matches_occasion(p.get("occasions"), occasion)
        ]
        matching_catalog_items.sort(key=lambda p: int(p.get("price_cents") or 0))

        budget_cents = int(body.budget_max * 100) if body.budget_max is not None and body.budget_max > 0 else None

        if budget_cents is not None:
            in_budget_items = [p for p in matching_catalog_items if int(p.get("price_cents") or 0) <= budget_cents]
            if in_budget_items:
                selected_prods = in_budget_items[:2]
                budget_status = "within_budget"
            elif matching_catalog_items:
                no_products_in_budget = True
                budget_status = "no_products_in_budget"
                cheapest_alt = _to_catalog_suggestion(matching_catalog_items[0]).model_dump()
                selected_prods = []
            else:
                selected_prods = []
                budget_status = "no_products_found"
        else:
            selected_prods = matching_catalog_items[:2]
            budget_status = "within_budget" if matching_catalog_items else "no_products_found"

        for prod in selected_prods:
            catalog_item_id = f"catalog_{prod['id']}"
            cat_engine_item = {
                "id": catalog_item_id,
                "category": prod.get("slot") or prod.get("category", fallback_slot),
                "slot": prod.get("slot", fallback_slot),
                "sub_category": prod.get("subtype") or prod.get("name"),
                "color": (prod.get("color_tags") or ["#111827"])[0],
                "colors": prod.get("color_tags") or [],
                "fit": prod.get("fit", "regular"),
                "formality": prod.get("formality", 1),
                "occasions": prod.get("occasions") or [occasion],
                "seasons": prod.get("seasons") or [season, "all_season"],
                "styles": prod.get("style_tags") or [],
                "pattern": prod.get("pattern", "solid"),
                "is_available": True,
                "source_type": "catalog",
            }

            mixed_candidates = generate_outfits(
                [*engine_items, cat_engine_item],
                occasion=occasion,
                season=season,
                body_shape=body_shape,
                attrs=attrs,
                affinities=affinities,
                limit=3,
            )

            # Filter candidates to only those containing this catalog item
            for cand in mixed_candidates:
                if catalog_item_id not in cand.item_ids:
                    continue

                outfit_id = str(uuid4())
                scores = feature_scores(cand, occasion=occasion, season=season, body_shape=body_shape, attrs=attrs)
                base_score = float(score_outfit(cand, occasion=occasion, season=season, body_shape=body_shape, attrs=attrs))
                affinity_delta, _ = compute_outfit_affinity_adjustment(cand, affinities) if affinities else (0.0, [])
                total_score = round(max(0.0, min(1.0, base_score + affinity_delta)), 3)

                reasons = explain_outfit(
                    cand,
                    occasion=occasion,
                    season=season,
                    body_shape=body_shape,
                    attrs=attrs,
                    affinities=affinities,
                )
                reasons.append(f"Mixed look adding {prod.get('name', 'catalog product')} to complete {fallback_slot} slot.")

                slot_items = []
                item_insert_rows = []

                for slot_name, item_dict in cand.slots.items():
                    raw_id = str(item_dict.get("id", ""))
                    if raw_id == catalog_item_id:
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

                metadata_payload = {
                    "fallback_reason": fallback_reason,
                    "unlocked_by_product_id": str(prod["id"]),
                }

                outfit_row = {
                    "id": outfit_id,
                    "user_id": user.id,
                    "occasion": occasion,
                    "vibe": body.vibe or "casual",
                    "skeleton": cand.skeleton,
                    "score": round(float(total_score), 3),
                    "component_scores": {k: round(float(v), 3) for k, v in scores.items()},
                    "reasons": reasons,
                    "wardrobe_only": False,
                    "is_saved": False,
                    "metadata": metadata_payload,
                    "created_at": now_iso,
                    "updated_at": now_iso,
                }

                try:
                    client.from_("outfits").insert(outfit_row).execute()
                    if item_insert_rows:
                        client.from_("outfit_items").insert(item_insert_rows).execute()
                except Exception as exc:
                    logger.warning(f"Could not persist mixed outfit {outfit_id}: {exc}")

                mixed_responses.append(
                    OutfitResponse(
                        id=outfit_id,
                        user_id=user.id,
                        occasion=occasion,
                        vibe=body.vibe,
                        skeleton=cand.skeleton,
                        score=round(float(total_score), 3),
                        component_scores={k: round(float(v), 3) for k, v in scores.items()},
                        reasons=reasons,
                        ai_summary=ai_summary,
                        wardrobe_only=False,
                        fallback_reason=fallback_reason,
                        unlocked_by_product_id=str(prod["id"]),
                        is_saved=False,
                        items=slot_items,
                        created_at=now_iso,
                    )
                )

    # 10. Combine: Return wardrobe-only outfits first, then mixed looks
    combined_outfits = (wardrobe_responses + mixed_responses)[:body.limit]

    outfit_status = "success"
    if not combined_outfits:
        if critical_missing:
            outfit_status = "missing_required_slots"
        else:
            outfit_status = "no_matching_combinations"

    message = None
    if no_products_in_budget:
        message = "No catalog products within your budget could complete an outfit. Consider the cheapest alternative."
    elif mixed_responses and wardrobe_responses:
        message = "Showing your wardrobe outfits followed by recommended mixed looks."
    elif mixed_responses and not wardrobe_responses:
        message = "Wardrobe was missing a required slot; showing outfits unlocked by catalog items."

    return GenerateOutfitsResponse(
        outfits=combined_outfits,
        status=outfit_status,
        message=message,
        missing_slots=critical_missing if not combined_outfits else [],
        profile_warning=profile_warning,
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
    summary="Get caller's saved looks",
)
async def list_saved_outfits(
    token: str = Depends(get_current_token),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Retrieves all outfits bookmarked/saved by the caller with populated items."""
    client = get_user_scoped_supabase_client(token)

    try:
        outfits_res = (
            client.from_("outfits")
            .select("*")
            .eq("user_id", user.id)
            .eq("is_saved", True)
            .order("updated_at", desc=True)
            .execute()
        )
    except Exception as exc:
        logger.error(f"Failed to fetch saved outfits for user {user.id}: {exc}")
        raise AppException(
            message="Unable to retrieve saved outfits.",
            code="SAVED_OUTFITS_FETCH_ERROR",
            status_code=500,
        )

    outfit_rows = outfits_res.data or []
    if not outfit_rows:
        return SavedOutfitsListResponse(outfits=[], total=0)

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
    for r in outfit_rows:
        o_id = r["id"]
        meta = r.get("metadata") or {}
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
                items=items_by_outfit.get(o_id, []),
                created_at=str(r.get("created_at", "")),
            )
        )

    return SavedOutfitsListResponse(outfits=results, total=len(results))


@router.post(
    "/{outfit_id}/save",
    summary="Save / bookmark an outfit look",
)
async def save_outfit(
    outfit_id: str,
    token: str = Depends(get_current_token),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Marks an outfit as saved/bookmarked."""
    client = get_user_scoped_supabase_client(token)
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        res = (
            client.from_("outfits")
            .update({"is_saved": True, "updated_at": now_iso})
            .eq("id", outfit_id)
            .eq("user_id", user.id)
            .execute()
        )
    except Exception as exc:
        logger.error(f"Failed to save outfit {outfit_id}: {exc}")
        raise AppException(message="Unable to save outfit.", code="SAVE_ERROR", status_code=500)

    if not res.data:
        raise AppException(message="Outfit not found or unauthorized.", code="NOT_FOUND", status_code=404)

    return {"success": True, "message": "Outfit saved to your collection."}


@router.delete(
    "/{outfit_id}/save",
    summary="Unsave an outfit look",
)
async def unsave_outfit(
    outfit_id: str,
    token: str = Depends(get_current_token),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Removes an outfit from saved/bookmarked status."""
    client = get_user_scoped_supabase_client(token)
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        res = (
            client.from_("outfits")
            .update({"is_saved": False, "updated_at": now_iso})
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

    # 2. Extract item attributes for transparent Style DNA derivation
    colors: set[str] = set()
    categories: set[str] = set()
    styles: set[str] = set()

    try:
        items_res = (
            client.from_("outfit_items")
            .select("slot, wardrobe_items(category, slot, sub_category, primary_color, color_tags, style_tags)")
            .eq("outfit_id", outfit_id)
            .execute()
        )
        for row in (items_res.data or []):
            slot = row.get("slot")
            if slot:
                categories.add(str(slot).lower())
            w_item = row.get("wardrobe_items") or {}
            if w_item.get("category"):
                categories.add(str(w_item["category"]).lower())
            if w_item.get("primary_color"):
                colors.add(str(w_item["primary_color"]).lower())
            for c in (w_item.get("color_tags") or []):
                colors.add(str(c).lower())
            for s in (w_item.get("style_tags") or []):
                styles.add(str(s).lower())
    except Exception as exc:
        logger.debug(f"Could not load items for event metadata: {exc}")

    event_id = str(uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()
    event_row = {
        "id": event_id,
        "user_id": user.id,
        "outfit_id": outfit_id,
        "event_type": body.event_type,
        "metadata": {
            "colors": sorted(list(colors)),
            "categories": sorted(list(categories)),
            "styles": sorted(list(styles)),
            "occasion": outfit_row.get("occasion"),
            **(body.metadata or {}),
        },
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
    if body.event_type == "save":
        try:
            client.from_("outfits").update({"is_saved": True, "updated_at": now_iso}).eq("id", outfit_id).execute()
        except Exception:
            pass
    elif body.event_type == "dislike":
        try:
            client.from_("outfits").update({"is_saved": False, "updated_at": now_iso}).eq("id", outfit_id).execute()
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
