from fastapi import APIRouter, Depends
from ..core.config import settings
from ..core.security import require_admin
from ..core.supabase import get_admin_supabase_client
from ..schemas.user import AuthenticatedUser

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/status")
async def get_admin_system_status(
    admin_user: AuthenticatedUser = Depends(require_admin),
) -> dict:
    """Provides secure, high-level operational status to verified administrators only.
    
    SECURITY: Replaces the previous public /api/debug route that leaked key presence
    and secret lengths. Does not disclose raw environment variables, key lengths, or secrets.
    """
    supabase_ok = False
    try:
        admin_client = get_admin_supabase_client()
        res = admin_client.from_("products").select("id", count="exact", head=True).execute()
        supabase_ok = res.count is not None
    except Exception:
        supabase_ok = False

    return {
        "status": "operational",
        "supabase_connected": supabase_ok,
        "ai_provider_configured": bool(settings.OPENROUTER_API_KEY and settings.OPENROUTER_API_KEY.strip()),
        "admin_caller": admin_user.email,
    }
