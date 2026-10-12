from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Request
from ..core.exceptions import AppException
from ..core.security import get_optional_user, require_admin
from ..core.supabase import get_admin_supabase_client, get_public_supabase_client
from ..schemas.analytics import (
    AnalyticsStatsResponse,
    EventTypeCount,
    RecentEvent,
    TopPage,
    TopProduct,
    TrackEventRequest,
    TrackEventResponse,
)
from ..schemas.user import AuthenticatedUser

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.post("/track", response_model=TrackEventResponse)
async def track_event(
    payload: TrackEventRequest,
    request: Request,
    optional_user: Optional[AuthenticatedUser] = Depends(get_optional_user),
) -> TrackEventResponse:
    """Records an analytics event and updates the active user session.
    
    Accepts events from both anonymous and authenticated visitors.
    """
    supabase = get_public_supabase_client()

    # Extract client IP and user agent safely
    client_ip = (
        request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or request.headers.get("x-real-ip")
        or (request.client.host if request.client else "unknown")
    )
    user_agent = request.headers.get("user-agent", "unknown")
    user_id = optional_user.id if optional_user else None

    insert_data = {
        "event_type": payload.event_type,
        "event_data": payload.event_data,
        "user_id": user_id,
        "session_id": payload.session_id,
        "ip_address": client_ip,
        "user_agent": user_agent,
    }

    event_id = None
    try:
        res = supabase.from_("analytics_events").insert(insert_data).execute()
        if res.data and len(res.data) > 0:
            event_id = str(res.data[0].get("id"))
    except Exception as e:
        # Analytics tracking should log errors without breaking the user experience
        pass

    # Update or create session
    try:
        now_iso = datetime.now(timezone.utc).isoformat()
        supabase.from_("user_sessions").upsert(
            {
                "session_id": payload.session_id,
                "user_id": user_id,
                "last_active_at": now_iso,
                "device_info": {"userAgent": user_agent},
            },
            on_conflict="session_id",
        ).execute()
    except Exception:
        pass

    return TrackEventResponse(success=True, event_id=event_id)


@router.get("/stats", response_model=AnalyticsStatsResponse)
async def get_analytics_stats(
    admin_user: AuthenticatedUser = Depends(require_admin),
) -> AnalyticsStatsResponse:
    """Retrieves aggregated analytics insights for the store.
    
    SECURITY: Strictly requires verified administrator authorization (require_admin).
    The previous hard-coded client-side password ('admin123') and unprotected GET route
    are eliminated in this flow.
    """
    admin_client = get_admin_supabase_client()

    now = datetime.now(timezone.utc)
    seven_days_ago = (now - timedelta(days=7)).isoformat()

    try:
        # Total counts
        total_events_res = admin_client.from_("analytics_events").select("*", count="exact", head=True).execute()
        total_sessions_res = admin_client.from_("user_sessions").select("*", count="exact", head=True).execute()
        page_views_res = admin_client.from_("analytics_events").select("*", count="exact", head=True).eq("event_type", "page_view").execute()
        product_views_res = admin_client.from_("analytics_events").select("*", count="exact", head=True).eq("event_type", "product_view").execute()
        searches_res = admin_client.from_("analytics_events").select("*", count="exact", head=True).eq("event_type", "search").execute()

        total_events = total_events_res.count or 0
        total_sessions = total_sessions_res.count or 0
        total_page_views = page_views_res.count or 0
        total_product_views = product_views_res.count or 0
        total_searches = searches_res.count or 0

        # Recent 100 events
        recent_res = (
            admin_client.from_("analytics_events")
            .select("id, event_type, event_data, created_at, user_id")
            .order("created_at", desc=True)
            .limit(100)
            .execute()
        )
        recent_data = recent_res.data or []
        recent_events = [
            RecentEvent(
                id=str(r.get("id")),
                event_type=r.get("event_type"),
                event_data=r.get("event_data") or {},
                created_at=r.get("created_at"),
                user_id=r.get("user_id"),
            )
            for r in recent_data
        ]

        # Top pages (past 7 days)
        page_events_res = (
            admin_client.from_("analytics_events")
            .select("event_data")
            .eq("event_type", "page_view")
            .gte("created_at", seven_days_ago)
            .execute()
        )
        page_counter = Counter(
            (ev.get("event_data") or {}).get("url", "unknown")
            for ev in (page_events_res.data or [])
        )
        top_pages = [
            TopPage(page=page, count=count)
            for page, count in page_counter.most_common(10)
        ]

        # Top products (past 7 days)
        prod_events_res = (
            admin_client.from_("analytics_events")
            .select("event_data")
            .eq("event_type", "product_view")
            .gte("created_at", seven_days_ago)
            .execute()
        )
        prod_counter: Counter = Counter()
        prod_names: dict = {}
        for ev in prod_events_res.data or []:
            data = ev.get("event_data") or {}
            p_id = data.get("productId") or data.get("product_id") or "unknown"
            p_name = data.get("productName") or data.get("name")
            prod_counter[p_id] += 1
            if p_name and p_id not in prod_names:
                prod_names[p_id] = p_name

        top_products = [
            TopProduct(product_id=p_id, name=prod_names.get(p_id), count=count)
            for p_id, count in prod_counter.most_common(10)
        ]

        # Events by type (past 7 days)
        type_events_res = (
            admin_client.from_("analytics_events")
            .select("event_type")
            .gte("created_at", seven_days_ago)
            .execute()
        )
        type_counter = Counter(
            ev.get("event_type", "unknown")
            for ev in (type_events_res.data or [])
        )
        events_by_type = [
            EventTypeCount(event_type=t, count=count)
            for t, count in type_counter.items()
        ]

    except Exception as e:
        raise AppException(
            message=f"Failed to aggregate analytics: {str(e)}",
            code="DATABASE_ERROR",
            status_code=500,
        )

    return AnalyticsStatsResponse(
        total_events=total_events,
        total_sessions=total_sessions,
        total_page_views=total_page_views,
        total_product_views=total_product_views,
        total_searches=total_searches,
        top_pages=top_pages,
        top_products=top_products,
        recent_events=recent_events,
        events_by_type=events_by_type,
    )
