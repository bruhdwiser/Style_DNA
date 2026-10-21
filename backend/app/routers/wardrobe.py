"""Wardrobe endpoints — private digital closet management.

Provides:
- Signed direct upload URL generation for browser-to-Supabase Storage uploads
- Upload finalization with magic-byte checks, Pillow re-encoding, EXIF stripping,
  thumbnail creation, and partial-upload cleanup
- Direct multipart upload alternative for local / direct flows
- Garment quick-tagging with deterministic taxonomy derivation and review status
- Item listing with signed private view URLs
- Per-slot coverage metrics and missing outfit slot identification
- Item editing and deletion with associated storage object cleanup
"""

from __future__ import annotations

import base64
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from ..core.config import settings
from ..core.exceptions import AppException
from ..core.image_processing import sanitize_and_process_image
from ..core.security import get_current_token, get_current_user
from ..core.supabase import get_admin_supabase_client, get_user_scoped_supabase_client
from ..schemas.user import AuthenticatedUser
from ..schemas.wardrobe import (
    FinalizeUploadRequest,
    TagSuggestionResponse,
    UploadUrlRequest,
    UploadUrlResponse,
    WardrobeCoverageResponse,
    WardrobeItemResponse,
    WardrobeItemUpdate,
    WardrobeListResponse,
)
from ..styling.taxonomy import (
    calculate_slot_coverage,
    derive_taxonomy_tags,
)

logger = logging.getLogger("flashfit.wardrobe")

router = APIRouter(prefix="/wardrobe", tags=["Wardrobe"])

STORAGE_BUCKET = "wardrobe"
SIGNED_URL_EXPIRY = 3600  # 1 hour for secure viewing


# ==============================================================================
# Helpers
# ==============================================================================


def _clean_filename(filename: str) -> str:
    """Sanitize filename to alphanumeric and safe characters."""
    clean = re.sub(r"[^a-zA-Z0-9_\.-]", "_", filename.strip())
    return clean[:64] or "image.jpg"


def _get_storage_signing_client(client: Any = None) -> Any:
    """Returns the admin Supabase client if available to sign URLs across folders,
    falling back to the user client."""
    try:
        return get_admin_supabase_client()
    except Exception:
        return client


def _build_signed_view_url(client: Any, path: Optional[str]) -> Optional[str]:
    """Generate a temporary signed URL for viewing a private storage object.
    Never returns a raw relative storage path to prevent client-side 404s.
    """
    if not path or not isinstance(path, str):
        return None
    if path.startswith("http://") or path.startswith("https://"):
        return path

    signing_client = _get_storage_signing_client(client)
    if not signing_client:
        return None

    try:
        res = signing_client.storage.from_(STORAGE_BUCKET).create_signed_url(path, SIGNED_URL_EXPIRY)
        if isinstance(res, dict):
            return res.get("signedUrl") or res.get("signed_url")
        if hasattr(res, "signed_url"):
            return getattr(res, "signed_url")
        if hasattr(res, "get"):
            return res.get("signedURL") or None
    except Exception as exc:
        logger.debug(f"Unable to create signed view URL for {path}: {exc}")
    return None


def _batch_build_signed_view_urls(paths: list[str], client: Any = None) -> dict[str, str]:
    """Batch-generates signed download URLs in a single Supabase Storage request.
    Avoids 2 * N sequential network roundtrips that block the event loop.
    """
    clean_paths = [p for p in set(paths) if p and isinstance(p, str) and not p.startswith("http")]
    signed_map: dict[str, str] = {}
    if not clean_paths:
        return signed_map

    signing_client = _get_storage_signing_client(client)
    if not signing_client:
        return signed_map

    try:
        res = signing_client.storage.from_(STORAGE_BUCKET).create_signed_urls(clean_paths, SIGNED_URL_EXPIRY)
        if isinstance(res, list):
            for item in res:
                if isinstance(item, dict):
                    p = item.get("path")
                    s_url = item.get("signedUrl") or item.get("signedURL")
                    if p and s_url:
                        signed_map[p] = s_url
    except Exception as exc:
        logger.warning(f"Batch URL signing failed for {len(clean_paths)} paths: {exc}")
    return signed_map


def _format_item_row(
    row: dict[str, Any],
    client: Any = None,
    signed_map: Optional[dict[str, str]] = None,
) -> WardrobeItemResponse:
    storage_path = str(row.get("storage_path") or "")
    thumbnail_path = row.get("thumbnail_path")

    # Resolve signed image URL
    if storage_path.startswith("http"):
        signed_image = storage_path
    elif signed_map and storage_path in signed_map:
        signed_image = signed_map[storage_path]
    elif storage_path:
        signed_image = _build_signed_view_url(client, storage_path)
    else:
        signed_image = None

    # Resolve signed thumbnail URL
    signed_thumb = None
    if thumbnail_path:
        thumb_str = str(thumbnail_path)
        if thumb_str.startswith("http"):
            signed_thumb = thumb_str
        elif signed_map and thumb_str in signed_map:
            signed_thumb = signed_map[thumb_str]
        else:
            signed_thumb = _build_signed_view_url(client, thumb_str)

    # Fall back to signed_image if thumbnail is missing or could not be signed
    if not signed_thumb:
        signed_thumb = signed_image

    return WardrobeItemResponse(
        id=str(row.get("id", "")),
        user_id=str(row.get("user_id", "")),
        image_url=str(row.get("image_url", "")),
        storage_path=storage_path,
        thumbnail_path=thumbnail_path,
        signed_image_url=signed_image,
        signed_thumbnail_url=signed_thumb,
        category=row.get("category", "top"),
        slot=row.get("slot", "top"),
        sub_category=row.get("sub_category"),
        color_tags=row.get("color_tags") or [],
        primary_color=row.get("primary_color"),
        fit=row.get("fit"),
        formality=row.get("formality", 1),
        occasions=row.get("occasions") or [],
        seasons=row.get("seasons") or [],
        style_tags=row.get("style_tags") or [],
        pattern=row.get("pattern", "solid"),
        neckline=row.get("neckline"),
        rise=row.get("rise"),
        length=row.get("length"),
        notes=row.get("notes"),
        needs_review=bool(row.get("needs_review", True)),
        metadata=row.get("metadata") or {},
        created_at=str(row.get("created_at", "")) if row.get("created_at") else None,
        updated_at=str(row.get("updated_at", "")) if row.get("updated_at") else None,
    )


# ==============================================================================
# Upload URLs & Finalization
# ==============================================================================


@router.post(
    "/upload-url",
    response_model=UploadUrlResponse,
    summary="Get signed direct upload URL for private storage",
)
async def get_upload_url(
    body: UploadUrlRequest,
    token: str = Depends(get_current_token),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Provides a signed upload URL targeting the caller's private folder.

    The client uploads directly to Supabase Storage before calling /finalize-upload.
    """
    client = get_user_scoped_supabase_client(token)
    safe_name = _clean_filename(body.filename)
    raw_path = f"{user.id}/raw_{uuid4().hex[:12]}_{safe_name}"

    try:
        signed_data = client.storage.from_(STORAGE_BUCKET).create_signed_upload_url(raw_path)
    except Exception as exc:
        logger.error(f"Failed to generate signed upload URL for user {user.id}: {exc}")
        raise AppException(
            message="Unable to create upload session.",
            code="STORAGE_SESSION_ERROR",
            status_code=500,
        )

    upload_url = signed_data.get("signed_url") or signed_data.get("signedUrl") or ""
    token_str = signed_data.get("token") or ""

    return UploadUrlResponse(
        upload_url=upload_url,
        token=token_str,
        storage_path=raw_path,
    )


@router.post(
    "/finalize-upload",
    response_model=WardrobeItemResponse,
    summary="Finalize and process a direct storage upload",
)
async def finalize_upload(
    body: FinalizeUploadRequest,
    token: str = Depends(get_current_token),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Verifies ownership of the uploaded path, sanitizes image data, strips EXIF,
    creates a thumbnail, derives taxonomy tags, and registers the item under caller's RLS.

    Cleans up partial files if any processing step fails.
    """
    # 1. Strict path ownership verification
    if not body.storage_path.startswith(f"{user.id}/") or ".." in body.storage_path:
        raise AppException(
            message="Storage path does not belong to the authenticated user.",
            code="UNAUTHORIZED_STORAGE_PATH",
            status_code=403,
        )

    client = get_user_scoped_supabase_client(token)

    # 2. Download the uploaded raw object from private storage
    try:
        raw_bytes = client.storage.from_(STORAGE_BUCKET).download(body.storage_path)
    except Exception as exc:
        logger.error(f"Failed to download raw uploaded file '{body.storage_path}': {exc}")
        raise AppException(
            message="Uploaded file not found or could not be retrieved from storage.",
            code="UPLOAD_DOWNLOAD_FAILED",
            status_code=400,
        )

    # 3. Sanitize and re-encode with Pillow (signature check, size limit, metadata strip)
    clean_path: Optional[str] = None
    thumb_path: Optional[str] = None
    item_id = str(uuid4())

    try:
        processed = sanitize_and_process_image(raw_bytes)

        clean_path = f"{user.id}/{item_id}.jpg"
        thumb_path = f"{user.id}/{item_id}_thumb.jpg"

        # Upload sanitized display image
        client.storage.from_(STORAGE_BUCKET).upload(
            clean_path,
            processed.display_bytes,
            {"content-type": "image/jpeg", "upsert": "true"},
        )

        # Upload thumbnail
        client.storage.from_(STORAGE_BUCKET).upload(
            thumb_path,
            processed.thumbnail_bytes,
            {"content-type": "image/jpeg", "upsert": "true"},
        )

        # Derive styling tags from quick-tag inputs
        derived = derive_taxonomy_tags(
            category=body.category,
            sub_category=body.sub_category,
            primary_color=body.primary_color,
            fit=body.fit,
        )

        row_data = {
            "id": item_id,
            "user_id": user.id,
            "image_url": clean_path,
            "storage_path": clean_path,
            "thumbnail_path": thumb_path,
            "category": body.category,
            "slot": derived["slot"],
            "sub_category": body.sub_category,
            "color_tags": derived["color_tags"],
            "primary_color": body.primary_color,
            "fit": body.fit,
            "formality": derived["formality"],
            "occasions": derived["occasions"],
            "seasons": derived["seasons"],
            "style_tags": derived["style_tags"],
            "pattern": body.pattern or "solid",
            "notes": body.notes,
            "needs_review": True,
            "metadata": processed.metadata,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        # Insert through caller-scoped client (RLS enforces user_id = auth.uid())
        insert_res = client.from_("wardrobe_items").insert(row_data).execute()
        if not insert_res.data:
            raise AppException("Failed to save wardrobe item record.", code="DB_INSERT_FAILED", status_code=500)

        # Clean up temporary raw upload
        try:
            client.storage.from_(STORAGE_BUCKET).remove([body.storage_path])
        except Exception:
            pass

        return _format_item_row(insert_res.data[0], client)

    except Exception as exc:
        # Partial upload cleanup
        cleanup_paths = [body.storage_path]
        if clean_path:
            cleanup_paths.append(clean_path)
        if thumb_path:
            cleanup_paths.append(thumb_path)

        try:
            client.storage.from_(STORAGE_BUCKET).remove(cleanup_paths)
        except Exception:
            pass

        if isinstance(exc, AppException):
            raise exc
        logger.error(f"Error finalizing wardrobe upload: {exc}")
        raise AppException(
            message=f"Image finalization failed: {str(exc)}",
            code="FINALIZATION_FAILED",
            status_code=500,
        )


@router.post(
    "/upload",
    response_model=WardrobeItemResponse,
    summary="Direct multipart file upload with validation and quick-tagging",
)
async def direct_upload(
    file: UploadFile = File(...),
    category: str = Form(...),
    sub_category: Optional[str] = Form(None),
    primary_color: Optional[str] = Form(None),
    fit: Optional[str] = Form(None),
    pattern: Optional[str] = Form("solid"),
    notes: Optional[str] = Form(None),
    token: str = Depends(get_current_token),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Direct multipart upload fallback that executes the exact same validation,
    Pillow re-encoding, thumbnail creation, and RLS insertion.
    """
    raw_bytes = await file.read()
    client = get_user_scoped_supabase_client(token)

    item_id = str(uuid4())
    clean_path = f"{user.id}/{item_id}.jpg"
    thumb_path = f"{user.id}/{item_id}_thumb.jpg"

    try:
        processed = sanitize_and_process_image(raw_bytes)

        client.storage.from_(STORAGE_BUCKET).upload(
            clean_path,
            processed.display_bytes,
            {"content-type": "image/jpeg", "upsert": "true"},
        )
        client.storage.from_(STORAGE_BUCKET).upload(
            thumb_path,
            processed.thumbnail_bytes,
            {"content-type": "image/jpeg", "upsert": "true"},
        )

        derived = derive_taxonomy_tags(
            category=category,
            sub_category=sub_category,
            primary_color=primary_color,
            fit=fit,
        )

        row_data = {
            "id": item_id,
            "user_id": user.id,
            "image_url": clean_path,
            "storage_path": clean_path,
            "thumbnail_path": thumb_path,
            "category": category,
            "slot": derived["slot"],
            "sub_category": sub_category,
            "color_tags": derived["color_tags"],
            "primary_color": primary_color,
            "fit": fit,
            "formality": derived["formality"],
            "occasions": derived["occasions"],
            "seasons": derived["seasons"],
            "style_tags": derived["style_tags"],
            "pattern": pattern or "solid",
            "notes": notes,
            "needs_review": True,
            "metadata": processed.metadata,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        insert_res = client.from_("wardrobe_items").insert(row_data).execute()
        if not insert_res.data:
            raise AppException("Failed to insert wardrobe item.", code="DB_INSERT_FAILED", status_code=500)

        return _format_item_row(insert_res.data[0], client)

    except Exception as exc:
        try:
            client.storage.from_(STORAGE_BUCKET).remove([clean_path, thumb_path])
        except Exception:
            pass

        if isinstance(exc, AppException):
            raise exc
        logger.error(f"Error during direct wardrobe upload: {exc}")
        raise AppException(
            message=f"Upload failed: {str(exc)}",
            code="DIRECT_UPLOAD_FAILED",
            status_code=500,
        )


# ==============================================================================
# Item Queries, Coverage & Mutations
# ==============================================================================


@router.get(
    "",
    response_model=WardrobeListResponse,
    summary="List caller's wardrobe items",
)
async def list_wardrobe_items(
    slot: Optional[str] = Query(None, description="Filter by garment slot"),
    category: Optional[str] = Query(None, description="Filter by category"),
    needs_review: Optional[bool] = Query(None, description="Filter by review status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    token: str = Depends(get_current_token),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Lists caller's wardrobe items with RLS enforcement and signed view URLs."""
    client = get_user_scoped_supabase_client(token)

    query = (
        client.from_("wardrobe_items")
        .select("*", count="exact")
        .eq("user_id", user.id)
    )

    if slot:
        query = query.eq("slot", slot.strip().lower())
    if category:
        query = query.eq("category", category.strip().lower())
    if needs_review is not None:
        query = query.eq("needs_review", needs_review)

    start_idx = (page - 1) * page_size
    query = query.order("created_at", desc=True).range(start_idx, start_idx + page_size - 1)

    try:
        res = query.execute()
    except Exception as exc:
        logger.error(f"Failed to query wardrobe items for user {user.id}: {exc}")
        raise AppException(
            message="Unable to retrieve wardrobe items.",
            code="WARDROBE_QUERY_ERROR",
            status_code=500,
        )

    rows = res.data or []
    total = res.count if res.count is not None else len(rows)

    # Collect all storage paths for batch URL signing (single roundtrip instead of 2 * N sequential calls)
    all_paths: list[str] = []
    for r in rows:
        sp = r.get("storage_path")
        tp = r.get("thumbnail_path")
        if sp and isinstance(sp, str):
            all_paths.append(sp)
        if tp and isinstance(tp, str):
            all_paths.append(tp)

    signed_map = _batch_build_signed_view_urls(all_paths, client)
    items = [_format_item_row(r, client, signed_map=signed_map) for r in rows]

    return WardrobeListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/coverage",
    response_model=WardrobeCoverageResponse,
    summary="Get slot coverage metrics and outfit readiness",
)
async def get_wardrobe_coverage(
    token: str = Depends(get_current_token),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Calculates distribution across core slots and identifies empty slots."""
    client = get_user_scoped_supabase_client(token)

    try:
        res = (
            client.from_("wardrobe_items")
            .select("slot, category, needs_review")
            .eq("user_id", user.id)
            .execute()
        )
    except Exception as exc:
        logger.error(f"Failed to fetch coverage for user {user.id}: {exc}")
        raise AppException(
            message="Unable to retrieve wardrobe coverage metrics.",
            code="COVERAGE_ERROR",
            status_code=500,
        )

    coverage = calculate_slot_coverage(res.data or [])
    return WardrobeCoverageResponse(**coverage)


@router.get(
    "/{item_id}",
    response_model=WardrobeItemResponse,
    summary="Get single wardrobe item",
)
async def get_wardrobe_item(
    item_id: str,
    token: str = Depends(get_current_token),
    user: AuthenticatedUser = Depends(get_current_user),
):
    client = get_user_scoped_supabase_client(token)

    try:
        res = (
            client.from_("wardrobe_items")
            .select("*")
            .eq("id", item_id)
            .eq("user_id", user.id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise AppException(message=f"Failed to fetch item: {exc}", code="ITEM_FETCH_ERROR", status_code=500)

    if not res.data:
        raise AppException(message="Wardrobe item not found.", code="ITEM_NOT_FOUND", status_code=404)

    return _format_item_row(res.data[0], client)


@router.patch(
    "/{item_id}",
    response_model=WardrobeItemResponse,
    summary="Update wardrobe item tags and review status",
)
async def update_wardrobe_item(
    item_id: str,
    body: WardrobeItemUpdate,
    token: str = Depends(get_current_token),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Updates attributes (slot, fit, occasions, formality, etc.) and allows
    marking needs_review as false.
    """
    client = get_user_scoped_supabase_client(token)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    try:
        res = (
            client.from_("wardrobe_items")
            .update(updates)
            .eq("id", item_id)
            .eq("user_id", user.id)
            .execute()
        )
    except Exception as exc:
        logger.error(f"Failed to update item {item_id}: {exc}")
        raise AppException(message="Failed to update item tags.", code="ITEM_UPDATE_ERROR", status_code=500)

    if not res.data:
        raise AppException(message="Wardrobe item not found or unauthorized.", code="ITEM_NOT_FOUND", status_code=404)

    return _format_item_row(res.data[0], client)


@router.delete(
    "/{item_id}",
    summary="Delete wardrobe item and remove storage images",
)
async def delete_wardrobe_item(
    item_id: str,
    token: str = Depends(get_current_token),
    user: AuthenticatedUser = Depends(get_current_user),
):
    client = get_user_scoped_supabase_client(token)

    # 1. Fetch paths before row deletion
    try:
        res = (
            client.from_("wardrobe_items")
            .select("storage_path, thumbnail_path")
            .eq("id", item_id)
            .eq("user_id", user.id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise AppException(message=f"Failed to find item: {exc}", code="ITEM_QUERY_ERROR", status_code=500)

    if not res.data:
        raise AppException(message="Wardrobe item not found.", code="ITEM_NOT_FOUND", status_code=404)

    row = res.data[0]
    storage_path = row.get("storage_path")
    thumbnail_path = row.get("thumbnail_path")

    # 2. Delete row from database
    try:
        client.from_("wardrobe_items").delete().eq("id", item_id).eq("user_id", user.id).execute()
    except Exception as exc:
        raise AppException(message=f"Failed to delete item row: {exc}", code="ITEM_DELETE_ERROR", status_code=500)

    # 3. Delete files from storage
    cleanup = [p for p in (storage_path, thumbnail_path) if p]
    if cleanup:
        try:
            client.storage.from_(STORAGE_BUCKET).remove(cleanup)
        except Exception as exc:
            logger.warning(f"Failed to delete storage objects {cleanup}: {exc}")

    return {"success": True, "message": "Wardrobe item and storage assets deleted."}


# ==============================================================================
# AI Photo Tag Suggestions (Optional OpenRouter Enhancement with Consent)
# ==============================================================================


@router.post(
    "/suggest-tags",
    response_model=TagSuggestionResponse,
    summary="Suggest styling tags from garment photo using OpenRouter or deterministic fallback",
)
async def suggest_garment_tags(
    storage_path: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    consent_confirmed: bool = Form(False),
    token: str = Depends(get_current_token),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Analyzes a garment photo to propose taxonomy-aligned styling tags.

    CRITICAL PRIVACY & SECURITY GUARANTEES:
    - Requires explicit revocable user consent before sending any photo.
    - NEVER sends personal information, profile data, or body measurements.
    - Validates all proposed tags against the strict server-side taxonomy.
    - Proposed tags always require user confirmation in the UI before saving.
    - Gracefully falls back to deterministic taxonomy templates if OpenRouter is unconfigured or unavailable.
    """
    client = get_user_scoped_supabase_client(token)

    # 1. Verify caller has granted consent for AI photo analysis
    has_consent = False
    try:
        consents_res = (
            client.from_("user_consents")
            .select("consent_type, granted")
            .eq("user_id", user.id)
            .in_("consent_type", ["wardrobe_photo_analysis", "photo_styling_ai"])
            .eq("granted", True)
            .execute()
        )
        has_consent = bool(consents_res.data)
    except Exception as exc:
        logger.warning(f"Could not check user consents: {exc}")

    if not has_consent:
        if consent_confirmed:
            try:
                now_iso = datetime.now(timezone.utc).isoformat()
                client.from_("user_consents").upsert(
                    {
                        "user_id": user.id,
                        "consent_type": "wardrobe_photo_analysis",
                        "granted": True,
                        "granted_at": now_iso,
                        "revoked_at": None,
                    },
                    on_conflict="user_id,consent_type",
                ).execute()
                has_consent = True
            except Exception as exc:
                logger.warning(f"Failed to record photo analysis consent: {exc}")
                has_consent = True
        else:
            raise AppException(
                message="Specific consent is required before analyzing wardrobe photos with AI. Please confirm consent.",
                code="CONSENT_REQUIRED",
                status_code=403,
            )

    # 2. Acquire raw image bytes
    raw_bytes: bytes = b""
    if file and file.filename:
        raw_bytes = await file.read()
    elif storage_path:
        if not storage_path.startswith(f"{user.id}/") or ".." in storage_path:
            raise AppException(
                message="Storage path does not belong to the authenticated user.",
                code="UNAUTHORIZED_STORAGE_PATH",
                status_code=403,
            )
        try:
            raw_bytes = client.storage.from_(STORAGE_BUCKET).download(storage_path)
        except Exception as exc:
            logger.error(f"Failed to download storage file '{storage_path}': {exc}")
            raise AppException(
                message="Could not read uploaded photo.",
                code="DOWNLOAD_FAILED",
                status_code=400,
            )
    else:
        raise AppException(
            message="No image file or storage_path provided.",
            code="IMAGE_REQUIRED",
            status_code=400,
        )

    # 3. Sanitize image with Pillow (magic bytes check, metadata strip, resize)
    try:
        processed = sanitize_and_process_image(raw_bytes)
    except Exception as exc:
        raise AppException(
            message=f"Invalid image file: {exc}",
            code="INVALID_IMAGE",
            status_code=400,
        )

    # 4. If OpenRouter is not configured, return deterministic taxonomy template
    if not settings.OPENROUTER_API_KEY or not settings.OPENROUTER_API_KEY.strip():
        derived = derive_taxonomy_tags(category="top", sub_category="t-shirt", primary_color="black", fit="regular")
        return TagSuggestionResponse(
            category="top",
            slot=derived["slot"],
            sub_category="T-Shirt",
            primary_color="black",
            color_tags=["#1a1a1a"],
            fit="regular",
            pattern="solid",
            formality=derived["formality"],
            occasions=derived["occasions"],
            seasons=derived["seasons"],
            style_tags=derived["style_tags"],
            source="deterministic_template",
            requires_user_confirmation=True,
            message="OpenRouter key unconfigured; applied deterministic taxonomy template.",
        )

    # 5. Call OpenRouter with sanitized thumbnail image (NO profile or body measurements sent)
    b64_img = base64.b64encode(processed.thumbnail_bytes).decode("utf-8")
    data_uri = f"data:image/jpeg;base64,{b64_img}"

    allowed_categories = ["top", "bottom", "dress", "saree", "ethnic_set", "layer", "shoes", "bag", "jewelry", "dupatta"]
    allowed_fits = ["regular", "slim", "relaxed", "oversized"]
    allowed_patterns = ["solid", "floral", "striped", "printed", "plaid", "geometric"]

    system_prompt = (
        "You are an expert fashion taxonomy classifier. Analyze the garment in the photo.\n"
        "Respond ONLY with a valid JSON object matching this schema:\n"
        "{\n"
        '  "category": "top" | "bottom" | "dress" | "saree" | "ethnic_set" | "layer" | "shoes" | "bag" | "jewelry" | "dupatta",\n'
        '  "sub_category": "<specific garment type, e.g. T-Shirt, Jeans, Saree, Kurta, Blazer, Sneakers>",\n'
        '  "primary_color": "<color name, e.g. black, white, navy, red, beige, green, pink>",\n'
        '  "fit": "regular" | "slim" | "relaxed" | "oversized",\n'
        '  "pattern": "solid" | "floral" | "striped" | "printed" | "plaid" | "geometric"\n'
        "}\n"
        "Do not include explanation or markdown formatting outside the JSON."
    )

    models_to_try = [
        "google/gemini-2.0-flash-001",
        "meta-llama/llama-3.2-11b-vision-instruct:free",
        settings.OPENROUTER_MODEL,
    ]

    for model in models_to_try:
        try:
            async with httpx.AsyncClient(timeout=20.0) as http_client:
                res = await http_client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": settings.SITE_URL,
                        "X-Title": "StyleSense Fashion AI",
                    },
                    json={
                        "model": model,
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": system_prompt},
                                    {"type": "image_url", "image_url": {"url": data_uri}},
                                ],
                            }
                        ],
                        "temperature": 0.2,
                        "max_tokens": 400,
                    },
                )
                if res.status_code == 200:
                    data = res.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    match = re.search(r"\{.*\}", content, re.DOTALL)
                    if match:
                        parsed = json.loads(match.group(0))
                        raw_cat = str(parsed.get("category", "top")).strip().lower()
                        cat = raw_cat if raw_cat in allowed_categories else "top"
                        sub_cat = str(parsed.get("sub_category", "T-Shirt")).strip().title()
                        raw_col = str(parsed.get("primary_color", "black")).strip().lower()
                        raw_fit = str(parsed.get("fit", "regular")).strip().lower()
                        fit = raw_fit if raw_fit in allowed_fits else "regular"
                        raw_pat = str(parsed.get("pattern", "solid")).strip().lower()
                        pattern = raw_pat if raw_pat in allowed_patterns else "solid"

                        derived = derive_taxonomy_tags(
                            category=cat,
                            sub_category=sub_cat,
                            primary_color=raw_col,
                            fit=fit,
                        )

                        return TagSuggestionResponse(
                            category=cat,
                            slot=derived["slot"],
                            sub_category=sub_cat,
                            primary_color=raw_col,
                            color_tags=derived["color_tags"],
                            fit=fit,
                            pattern=pattern,
                            formality=derived["formality"],
                            occasions=derived["occasions"],
                            seasons=derived["seasons"],
                            style_tags=derived["style_tags"],
                            source="openrouter",
                            requires_user_confirmation=True,
                            message="AI proposed styling tags based on your photo. Please review and confirm.",
                        )
        except Exception as exc:
            logger.warning(f"OpenRouter vision tag suggestion failed with model '{model}': {exc}")
            continue

    # 6. Fallback if vision models failed or timed out
    derived = derive_taxonomy_tags(category="top", sub_category="t-shirt", primary_color="black", fit="regular")
    return TagSuggestionResponse(
        category="top",
        slot=derived["slot"],
        sub_category="T-Shirt",
        primary_color="black",
        color_tags=["#1a1a1a"],
        fit="regular",
        pattern="solid",
        formality=derived["formality"],
        occasions=derived["occasions"],
        seasons=derived["seasons"],
        style_tags=derived["style_tags"],
        source="deterministic_fallback",
        requires_user_confirmation=True,
        message="AI suggestion unavailable. Deterministic taxonomy template applied.",
    )

