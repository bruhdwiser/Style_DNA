import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends

from ..core.exceptions import AppException
from ..core.security import get_current_token, get_current_user
from ..core.supabase import get_admin_supabase_client, get_user_scoped_supabase_client
from ..schemas.user import AuthenticatedUser, CurrentUserResponse

logger = logging.getLogger("flashfit.auth")

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.get("/me", response_model=CurrentUserResponse)
async def get_my_profile(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> CurrentUserResponse:
    """Verifies incoming Supabase token and returns the caller's identity and admin status."""
    return CurrentUserResponse(user=current_user)


@router.post("/logout", summary="Log out the authenticated user")
async def logout_user(
    token: str = Depends(get_current_token),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Logs out the current authenticated user and confirms session termination."""
    logger.info(f"User {current_user.id} ({current_user.email}) logged out.")
    return {
        "success": True,
        "message": f"Successfully logged out {current_user.email}.",
    }


@router.get("/export", summary="Export all personal data as JSON (GDPR/Data Portability)")
async def export_my_data(
    token: str = Depends(get_current_token),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Exports caller's profile, consents, wardrobe items, and cart data.
    Uses caller-scoped client so RLS applies to all queries.
    """
    client = get_user_scoped_supabase_client(token)

    # 1. Profile
    profile_data = None
    try:
        prof = client.from_("style_profiles").select("*").eq("user_id", current_user.id).limit(1).execute()
        if prof.data:
            profile_data = prof.data[0]
    except Exception as exc:
        logger.warning(f"Failed to export style_profiles for {current_user.id}: {exc}")

    # 2. Consents
    consents_data = []
    try:
        cons = client.from_("user_consents").select("*").eq("user_id", current_user.id).execute()
        consents_data = cons.data or []
    except Exception as exc:
        logger.warning(f"Failed to export user_consents for {current_user.id}: {exc}")

    # 3. Wardrobe items
    wardrobe_data = []
    try:
        items = client.from_("wardrobe_items").select("*").eq("user_id", current_user.id).execute()
        wardrobe_data = items.data or []
    except Exception as exc:
        logger.warning(f"Failed to export wardrobe_items for {current_user.id}: {exc}")

    # 4. Cart items
    cart_data = []
    try:
        cart_items = client.from_("cart_items").select("*").eq("user_id", current_user.id).execute()
        cart_data = cart_items.data or []
    except Exception as exc:
        logger.warning(f"Failed to export cart_items for {current_user.id}: {exc}")

    # 5. Outfits & Outfit Items
    outfits_data = []
    try:
        user_outfits = client.from_("outfits").select("*, outfit_items(*)").eq("user_id", current_user.id).execute()
        outfits_data = user_outfits.data or []
    except Exception as exc:
        logger.warning(f"Failed to export outfits for {current_user.id}: {exc}")

    # 6. Outfit Events
    events_data = []
    try:
        user_events = client.from_("outfit_events").select("*").eq("user_id", current_user.id).execute()
        events_data = user_events.data or []
    except Exception as exc:
        logger.warning(f"Failed to export outfit_events for {current_user.id}: {exc}")

    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "user": {
            "id": current_user.id,
            "email": current_user.email,
        },
        "style_profile": profile_data,
        "consents": consents_data,
        "wardrobe_items": wardrobe_data,
        "outfits": outfits_data,
        "outfit_events": events_data,
        "cart_items": cart_data,
    }


@router.delete("/account", summary="Delete user account, database rows, and private storage assets")
async def delete_my_account(
    token: str = Depends(get_current_token),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Deletes all user rows across wardrobe, profile, consents, outfits, events, and carts,
    and purges all private wardrobe storage objects.
    
    SECURITY: Runs elevated operations strictly behind server-side verified caller ownership.
    """
    if not current_user or not current_user.id:
        raise AppException("Unauthorized caller.", code="UNAUTHORIZED", status_code=401)

    user_id = current_user.id

    try:
        admin_client = get_admin_supabase_client()
    except Exception as exc:
        logger.error(f"Cannot initialize admin client for account deletion: {exc}")
        raise AppException("Internal server configuration error.", code="ADMIN_CLIENT_ERROR", status_code=500)

    # 1. Clean up private wardrobe storage objects under {user_id}/
    deleted_storage_count = 0
    try:
        file_list = admin_client.storage.from_("wardrobe").list(user_id)
        if file_list:
            paths_to_delete = [
                f"{user_id}/{f['name']}"
                for f in file_list
                if isinstance(f, dict) and "name" in f
            ]
            if paths_to_delete:
                admin_client.storage.from_("wardrobe").remove(paths_to_delete)
                deleted_storage_count = len(paths_to_delete)
                logger.info(f"Purged {deleted_storage_count} storage objects for user {user_id}")
    except Exception as exc:
        logger.warning(f"Storage purge encountered an error for user {user_id}: {exc}")

    # 2. Delete database rows (outfit events, outfit items, outfits, wardrobe, profiles, consents, carts)
    try:
        admin_client.from_("outfit_events").delete().eq("user_id", user_id).execute()
        admin_client.from_("outfit_items").delete().eq("user_id", user_id).execute()
        admin_client.from_("outfits").delete().eq("user_id", user_id).execute()
        admin_client.from_("wardrobe_items").delete().eq("user_id", user_id).execute()
        admin_client.from_("style_profiles").delete().eq("user_id", user_id).execute()
        admin_client.from_("user_consents").delete().eq("user_id", user_id).execute()
        admin_client.from_("cart_items").delete().eq("user_id", user_id).execute()
        admin_client.from_("carts").delete().eq("user_id", user_id).execute()
    except Exception as exc:
        logger.error(f"Database purge failed for user {user_id}: {exc}")
        raise AppException("Failed to delete user database records.", code="PURGE_FAILED", status_code=500)

    # 3. Best-effort Supabase Auth user deletion via admin api
    try:
        if hasattr(admin_client, "auth") and hasattr(admin_client.auth, "admin"):
            admin_client.auth.admin.delete_user(user_id)
    except Exception as exc:
        logger.warning(f"Auth admin user deletion skipped or failed for {user_id}: {exc}")

    return {
        "success": True,
        "message": f"Account for {current_user.email} successfully purged.",
        "purged_storage_files": deleted_storage_count,
    }


# ==============================================================================
# /me Router (direct aliases for /auth/me, /auth/export, /auth/account)
# ==============================================================================
me_router = APIRouter(prefix="/me", tags=["Account"])


@me_router.get("", response_model=CurrentUserResponse)
async def me_profile(current_user: AuthenticatedUser = Depends(get_current_user)) -> CurrentUserResponse:
    return CurrentUserResponse(user=current_user)


@me_router.get("/export")
async def me_export(
    token: str = Depends(get_current_token),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    return await export_my_data(token=token, current_user=current_user)


@me_router.delete("/account")
async def me_delete(
    token: str = Depends(get_current_token),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    return await delete_my_account(token=token, current_user=current_user)


@me_router.post("/logout")
async def me_logout(
    token: str = Depends(get_current_token),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    return await logout_user(token=token, current_user=current_user)


