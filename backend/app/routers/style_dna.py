"""Style DNA API Router.

Exposes endpoints for viewing transparent, normalized style affinities
and resetting recorded outfit feedback history.
All operations are scoped to the authenticated caller (preserving RLS).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends

from ..core.exceptions import AppException
from ..core.security import get_current_token, get_current_user
from ..core.supabase import get_user_scoped_supabase_client
from ..schemas.style_dna import ResetStyleDnaResponse, StyleDnaResponse
from ..schemas.user import AuthenticatedUser
from ..styling.learning import calculate_affinities

logger = logging.getLogger("flashfit.style_dna")

router = APIRouter(prefix="/style-dna", tags=["Style DNA"])


@router.get(
    "",
    response_model=StyleDnaResponse,
    summary="Get caller's normalized Style DNA affinities and event summary",
)
async def get_user_style_dna(
    token: str = Depends(get_current_token),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Retrieve normalized affinities and event counts derived from caller's feedback.

    - Fully transparent, explainable preference tallies (no neural networks or black-box models).
    - Hard bounds on ranking influence (max +/-0.08) ensure occasion and outfit validity always dominate.
    """
    client = get_user_scoped_supabase_client(token)

    try:
        events_res = (
            client.from_("outfit_events")
            .select("*")
            .eq("user_id", user.id)
            .order("created_at", desc=True)
            .execute()
        )
    except Exception as exc:
        logger.error(f"Failed to fetch outfit events for user {user.id}: {exc}")
        raise AppException(
            message="Unable to load style DNA events.",
            code="STYLE_DNA_FETCH_ERROR",
            status_code=500,
        )

    events: list[dict[str, Any]] = events_res.data or []
    affinities_data = calculate_affinities(events)

    return StyleDnaResponse(
        total_events=affinities_data["total_events"],
        event_counts=affinities_data["event_counts"],
        affinities=affinities_data["affinities"],
        top_preferences=affinities_data["top_preferences"],
        avoidances=affinities_data["avoidances"],
        influence_cap=affinities_data["influence_cap"],
        message="Style DNA computed deterministically from your recorded outfit interactions.",
    )


@router.post(
    "/reset",
    response_model=ResetStyleDnaResponse,
    summary="Reset caller's Style DNA and feedback events",
)
async def reset_user_style_dna(
    token: str = Depends(get_current_token),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Deletes all recorded outfit events for caller, resetting affinities back to neutral."""
    client = get_user_scoped_supabase_client(token)

    try:
        client.from_("outfit_events").delete().eq("user_id", user.id).execute()
    except Exception as exc:
        logger.error(f"Failed to reset style events for user {user.id}: {exc}")
        raise AppException(
            message="Failed to reset style DNA.",
            code="STYLE_DNA_RESET_ERROR",
            status_code=500,
        )

    return ResetStyleDnaResponse(
        success=True,
        message="Your Style DNA and event history have been successfully reset to neutral.",
    )
