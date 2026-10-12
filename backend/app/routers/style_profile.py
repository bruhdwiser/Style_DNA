"""Style-profile and consent API endpoints.

Every query runs through the caller's user-scoped Supabase client so that
PostgreSQL Row Level Security enforces ownership — the server never bypasses
RLS for profile or consent reads/writes.

Body guidance is derived in-memory from the styling engine and persisted only
when the user has granted revocable `body_guidance_storage` consent.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends

from ..core.exceptions import AppException
from ..core.security import get_current_token, get_current_user
from ..core.supabase import get_user_scoped_supabase_client
from ..schemas.style_profile import (
    ConsentGrant,
    ConsentListResponse,
    ConsentResponse,
    StyleProfileResponse,
    StyleProfileUpdate,
)
from ..schemas.user import AuthenticatedUser

logger = logging.getLogger("flashfit.style_profile")

router = APIRouter(prefix="/style-profile", tags=["Style Profile"])


# ==============================================================================
# Helpers
# ==============================================================================


def _profile_row_to_response(row: dict) -> StyleProfileResponse:
    """Convert a Supabase row dict to a StyleProfileResponse."""
    return StyleProfileResponse(
        user_id=str(row.get("user_id", "")),
        favorite_styles=row.get("favorite_styles") or [],
        favorite_colors=row.get("favorite_colors") or [],
        budget_min=row.get("budget_min"),
        budget_max=row.get("budget_max"),
        occasions=row.get("occasions") or [],
        body_type=row.get("body_type"),
        body_guidance=row.get("body_guidance"),
        onboarding_complete=bool(row.get("onboarding_complete", False)),
        created_at=str(row.get("created_at", "")) if row.get("created_at") else None,
        updated_at=str(row.get("updated_at", "")) if row.get("updated_at") else None,
    )


def _consent_row_to_response(row: dict) -> ConsentResponse:
    return ConsentResponse(
        consent_type=row.get("consent_type", ""),
        granted=bool(row.get("granted", False)),
        granted_at=str(row.get("granted_at", "")) if row.get("granted_at") else None,
        revoked_at=str(row.get("revoked_at", "")) if row.get("revoked_at") else None,
    )


async def _has_consent(client, user_id: str, consent_type: str) -> bool:
    """Check whether the user currently has an active consent grant."""
    try:
        result = (
            client.from_("user_consents")
            .select("granted")
            .eq("user_id", user_id)
            .eq("consent_type", consent_type)
            .limit(1)
            .execute()
        )
        if result.data and len(result.data) > 0:
            return bool(result.data[0].get("granted", False))
    except Exception:
        pass
    return False


def _derive_body_guidance(body_type: Optional[str]) -> Optional[dict]:
    """Derive neutral fit guidance from the styling engine.

    Returns structured guidance that the frontend can display.
    Raw measurements are never involved — this is purely shape-based.
    """
    if not body_type:
        return None

    from ..styling.body_fit import _BODY_RULES

    source_rules = _BODY_RULES.get("manual", {})
    shape_prefs = source_rules.get(body_type)
    if not shape_prefs:
        return None

    guidance: dict = {
        "body_type": body_type,
        "recommendations": {},
    }
    for attr, values in shape_prefs.items():
        # Sort by preference weight descending
        sorted_values = sorted(values.items(), key=lambda x: x[1], reverse=True)
        top_picks = [v[0].replace("_", " ").title() for v in sorted_values[:3]]
        guidance["recommendations"][attr] = top_picks

    return guidance


# ==============================================================================
# Style Profile endpoints
# ==============================================================================


@router.get(
    "",
    response_model=StyleProfileResponse,
    summary="Get current user's style profile",
)
async def get_style_profile(
    token: str = Depends(get_current_token),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Returns the caller's style profile, or a blank default if none exists."""
    client = get_user_scoped_supabase_client(token)

    try:
        result = (
            client.from_("style_profiles")
            .select("*")
            .eq("user_id", user.id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.error(f"Failed to read style profile for user {user.id}: {exc}")
        raise AppException(
            message="Unable to retrieve style profile",
            code="PROFILE_READ_ERROR",
            status_code=500,
        )

    if result.data and len(result.data) > 0:
        return _profile_row_to_response(result.data[0])

    # Return empty default (no row exists yet)
    return StyleProfileResponse(
        user_id=user.id,
        favorite_styles=[],
        favorite_colors=[],
        budget_min=None,
        budget_max=None,
        occasions=[],
        body_type=None,
        body_guidance=None,
        onboarding_complete=False,
    )


@router.put(
    "",
    response_model=StyleProfileResponse,
    summary="Create or update style profile",
)
async def upsert_style_profile(
    body: StyleProfileUpdate,
    token: str = Depends(get_current_token),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Upserts the caller's style profile.

    - Body type is self-selected and optional.
    - Body guidance is derived in-memory and stored only with active consent.
    - Raw measurements are never stored.
    """
    client = get_user_scoped_supabase_client(token)
    now_iso = datetime.now(timezone.utc).isoformat()

    # Derive body guidance in memory
    guidance = _derive_body_guidance(body.body_type)

    # Only persist guidance if the user has granted body_guidance_storage consent
    persist_guidance = False
    if guidance:
        persist_guidance = await _has_consent(client, user.id, "body_guidance_storage")

    row_data = {
        "user_id": user.id,
        "favorite_styles": body.favorite_styles,
        "favorite_colors": body.favorite_colors,
        "budget_min": body.budget_min,
        "budget_max": body.budget_max,
        "occasions": body.occasions,
        "body_type": body.body_type,
        "body_guidance": guidance if persist_guidance else None,
        "onboarding_complete": body.onboarding_complete,
        "updated_at": now_iso,
    }

    try:
        # Try update first
        existing = (
            client.from_("style_profiles")
            .select("user_id")
            .eq("user_id", user.id)
            .limit(1)
            .execute()
        )

        if existing.data and len(existing.data) > 0:
            result = (
                client.from_("style_profiles")
                .update(row_data)
                .eq("user_id", user.id)
                .execute()
            )
        else:
            row_data["created_at"] = now_iso
            result = (
                client.from_("style_profiles")
                .insert(row_data)
                .execute()
            )
    except Exception as exc:
        logger.error(f"Failed to upsert style profile for user {user.id}: {exc}")
        raise AppException(
            message="Unable to save style profile",
            code="PROFILE_WRITE_ERROR",
            status_code=500,
        )

    if result.data and len(result.data) > 0:
        return _profile_row_to_response(result.data[0])

    # Re-fetch to return current state
    refetch = (
        client.from_("style_profiles")
        .select("*")
        .eq("user_id", user.id)
        .limit(1)
        .execute()
    )
    if refetch.data and len(refetch.data) > 0:
        return _profile_row_to_response(refetch.data[0])

    return StyleProfileResponse(user_id=user.id, **body.model_dump())


@router.delete(
    "/body-guidance",
    summary="Delete stored body guidance",
)
async def delete_body_guidance(
    token: str = Depends(get_current_token),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Lets the user delete their stored body-fit guidance at any time."""
    client = get_user_scoped_supabase_client(token)
    try:
        client.from_("style_profiles").update(
            {"body_guidance": None, "updated_at": datetime.now(timezone.utc).isoformat()}
        ).eq("user_id", user.id).execute()
    except Exception as exc:
        logger.error(f"Failed to delete body guidance for user {user.id}: {exc}")
        raise AppException(
            message="Unable to delete body guidance",
            code="GUIDANCE_DELETE_ERROR",
            status_code=500,
        )
    return {"success": True, "message": "Body guidance deleted"}


# ==============================================================================
# Consent endpoints
# ==============================================================================


@router.get(
    "/consents",
    response_model=ConsentListResponse,
    summary="List user's consent records",
)
async def list_consents(
    token: str = Depends(get_current_token),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Returns all consent records for the calling user."""
    client = get_user_scoped_supabase_client(token)
    try:
        result = (
            client.from_("user_consents")
            .select("*")
            .eq("user_id", user.id)
            .execute()
        )
    except Exception as exc:
        logger.error(f"Failed to read consents for user {user.id}: {exc}")
        raise AppException(
            message="Unable to retrieve consent records",
            code="CONSENT_READ_ERROR",
            status_code=500,
        )

    consents = [_consent_row_to_response(r) for r in (result.data or [])]
    return ConsentListResponse(consents=consents)


@router.put(
    "/consents",
    response_model=ConsentResponse,
    summary="Grant or revoke a consent",
)
async def upsert_consent(
    body: ConsentGrant,
    token: str = Depends(get_current_token),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Grants or revokes a specific consent type.

    When body_guidance_storage is revoked, existing body_guidance is also deleted.
    """
    client = get_user_scoped_supabase_client(token)
    now_iso = datetime.now(timezone.utc).isoformat()

    row_data = {
        "user_id": user.id,
        "consent_type": body.consent_type,
        "granted": body.granted,
    }

    if body.granted:
        row_data["granted_at"] = now_iso
        row_data["revoked_at"] = None
    else:
        row_data["revoked_at"] = now_iso

    try:
        # Check for existing consent
        existing = (
            client.from_("user_consents")
            .select("id")
            .eq("user_id", user.id)
            .eq("consent_type", body.consent_type)
            .limit(1)
            .execute()
        )

        if existing.data and len(existing.data) > 0:
            result = (
                client.from_("user_consents")
                .update(row_data)
                .eq("user_id", user.id)
                .eq("consent_type", body.consent_type)
                .execute()
            )
        else:
            result = (
                client.from_("user_consents")
                .insert(row_data)
                .execute()
            )
    except Exception as exc:
        logger.error(f"Failed to upsert consent for user {user.id}: {exc}")
        raise AppException(
            message="Unable to save consent",
            code="CONSENT_WRITE_ERROR",
            status_code=500,
        )

    # If revoking body_guidance_storage, also delete stored guidance
    if body.consent_type == "body_guidance_storage" and not body.granted:
        try:
            client.from_("style_profiles").update(
                {"body_guidance": None, "updated_at": now_iso}
            ).eq("user_id", user.id).execute()
            logger.info(f"Deleted body guidance for user {user.id} after consent revocation")
        except Exception:
            logger.warning(f"Failed to clear body guidance after consent revocation for user {user.id}")

    if result.data and len(result.data) > 0:
        return _consent_row_to_response(result.data[0])

    # Re-fetch
    refetch = (
        client.from_("user_consents")
        .select("*")
        .eq("user_id", user.id)
        .eq("consent_type", body.consent_type)
        .limit(1)
        .execute()
    )
    if refetch.data and len(refetch.data) > 0:
        return _consent_row_to_response(refetch.data[0])

    return ConsentResponse(
        consent_type=body.consent_type,
        granted=body.granted,
        granted_at=now_iso if body.granted else None,
        revoked_at=now_iso if not body.granted else None,
    )
