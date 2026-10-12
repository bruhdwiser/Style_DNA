from typing import Optional
from supabase import create_client, Client, ClientOptions
from .config import settings
from .exceptions import AppException


def get_public_supabase_client() -> Client:
    """Returns a Supabase client configured with the public anonymous key.
    
    Safe for public catalog queries and operations that do not require elevated privileges.
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        raise AppException(
            message="Supabase is not configured. Missing SUPABASE_URL or SUPABASE_ANON_KEY.",
            code="CONFIG_ERROR",
            status_code=500,
        )
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)


def get_user_scoped_supabase_client(token: str) -> Client:
    """Returns a Supabase client scoped to the authenticated user via their verified JWT.
    
    CRITICAL: This preserves PostgreSQL Row Level Security (RLS) by passing the user's
    access token in the Authorization header. PostgREST will execute all queries with
    auth.uid() set to the user's ID and auth.role() set to 'authenticated'.
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        raise AppException(
            message="Supabase is not configured. Missing SUPABASE_URL or SUPABASE_ANON_KEY.",
            code="CONFIG_ERROR",
            status_code=500,
        )
    
    options = ClientOptions(
        headers={"Authorization": f"Bearer {token}"},
        auto_refresh_token=False,
        persist_session=False,
    )
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY, options=options)


def get_admin_supabase_client() -> Client:
    """Returns a Supabase client configured with the SERVICE ROLE KEY.
    
    CRITICAL SECURITY NOTICE:
    - This client bypasses PostgreSQL Row Level Security (RLS).
    - It must NEVER be exposed or passed to untrusted clients.
    - It must only be used within the server after explicit server-side authorization
      checks (e.g., verifying user exists in public.admin_users).
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise AppException(
            message="Supabase service role is not configured. Missing SUPABASE_SERVICE_ROLE_KEY.",
            code="CONFIG_ERROR",
            status_code=500,
        )
    
    options = ClientOptions(
        auto_refresh_token=False,
        persist_session=False,
    )
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY, options=options)
