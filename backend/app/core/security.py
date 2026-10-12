import httpx
import jwt
from typing import Optional
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from .config import settings
from .exceptions import ForbiddenException, UnauthorizedException
from .supabase import get_admin_supabase_client
from ..schemas.user import AuthenticatedUser

# Security scheme for Swagger UI and header parsing
bearer_scheme = HTTPBearer(auto_error=False)


async def verify_supabase_token(token: str) -> dict:
    """Verifies a Supabase access token using supported server-side verification methods.
    
    CRITICAL: Never accepts an unverified decoded JWT.
    
    Verification hierarchy:
    1. If SUPABASE_JWT_SECRET is configured:
       Cryptographically verifies the HMAC-SHA256 signature, expiry (exp), and audience ('authenticated').
    2. Otherwise, verifies against Supabase GoTrue Auth service (GET /auth/v1/user):
       Supabase server verifies the signature, active user status, and revocation state.
    """
    if not token or not token.strip():
        raise UnauthorizedException("Authentication token is missing")

    # Method 1: Cryptographic verification via JWT Secret if configured (HS256)
    if settings.SUPABASE_JWT_SECRET:
        try:
            # Check algorithm header
            unverified_header = jwt.get_unverified_header(token)
            alg = unverified_header.get("alg", "HS256")
            
            if alg == "HS256":
                payload = jwt.decode(
                    token,
                    settings.SUPABASE_JWT_SECRET,
                    algorithms=["HS256"],
                    audience="authenticated",
                    options={"verify_exp": True, "verify_aud": True},
                )
                return {
                    "id": payload.get("sub"),
                    "email": payload.get("email"),
                    "role": payload.get("role", "authenticated"),
                    "app_metadata": payload.get("app_metadata", {}),
                    "user_metadata": payload.get("user_metadata", {}),
                }
            # If algorithm is asymmetric (e.g. RS256/ES256), proceed to Supabase GoTrue endpoint
        except jwt.ExpiredSignatureError:
            raise UnauthorizedException("Authentication token has expired")
        except jwt.PyJWTError as e:
            # Fall through to Supabase GoTrue verification in case secret/algorithm differs
            pass

    # Method 2: Official Supabase GoTrue verification endpoint (authoritative server-side check)
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        raise UnauthorizedException("Supabase authentication is not configured on the server")

    auth_url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/user"
    headers = {
        "apikey": settings.SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {token}",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(auth_url, headers=headers)
            if response.status_code != 200:
                raise UnauthorizedException("Token verification failed with Supabase Auth")
            data = response.json()
            return {
                "id": data.get("id"),
                "email": data.get("email"),
                "role": data.get("role", "authenticated"),
                "app_metadata": data.get("app_metadata", {}),
                "user_metadata": data.get("user_metadata", {}),
            }
    except httpx.RequestError as e:
        raise UnauthorizedException(f"Unable to reach Supabase authentication service: {str(e)}")


async def check_user_admin_status(user_id: str, email: Optional[str] = None) -> bool:
    """Verifies whether the given user has verified admin privileges.
    
    Checks:
    1. Server configuration allowlist (ADMIN_USER_IDS and ADMIN_EMAILS)
    2. Supabase database public.admin_users role
    Never trusts client-supplied role or claim.
    """
    # 1. Config-backed server allowlist check
    if user_id in settings.ADMIN_USER_IDS:
        return True
    if email and any(email.lower() == e.lower() for e in settings.ADMIN_EMAILS):
        return True

    # 2. Database table public.admin_users check
    if not settings.SUPABASE_SERVICE_ROLE_KEY:
        return False

    try:
        admin_client = get_admin_supabase_client()
        result = (
            admin_client.from_("admin_users")
            .select("id, role")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if result.data and len(result.data) > 0:
            role = result.data[0].get("role", "")
            return role in ("admin", "super_admin")
    except Exception:
        # Deny by default if lookup fails
        return False
    return False


async def get_current_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> str:
    """Extracts the raw bearer token string from the Authorization header."""
    if not credentials or not credentials.credentials:
        raise UnauthorizedException("Authorization header with Bearer token is required")
    return credentials.credentials


async def get_current_user(
    token: str = Depends(get_current_token),
) -> AuthenticatedUser:
    """Validates the incoming token and returns an AuthenticatedUser model.
    
    Rejects missing, forged, or expired tokens.
    """
    user_data = await verify_supabase_token(token)
    user_id = user_data.get("id")
    if not user_id:
        raise UnauthorizedException("Token does not contain a valid user identity")

    user_email = user_data.get("email")
    is_admin = await check_user_admin_status(user_id, email=user_email)

    return AuthenticatedUser(
        id=user_id,
        email=user_email,
        role=user_data.get("role", "authenticated"),
        is_admin=is_admin,
        app_metadata=user_data.get("app_metadata", {}),
        user_metadata=user_data.get("user_metadata", {}),
    )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[AuthenticatedUser]:
    """Extracts and verifies user token if present, returns None for anonymous requests."""
    if not credentials or not credentials.credentials:
        return None
    try:
        user_data = await verify_supabase_token(credentials.credentials)
        user_id = user_data.get("id")
        if not user_id:
            return None
        user_email = user_data.get("email")
        is_admin = await check_user_admin_status(user_id, email=user_email)
        return AuthenticatedUser(
            id=user_id,
            email=user_email,
            role=user_data.get("role", "authenticated"),
            is_admin=is_admin,
            app_metadata=user_data.get("app_metadata", {}),
            user_metadata=user_data.get("user_metadata", {}),
        )
    except UnauthorizedException:
        return None


async def require_admin(
    user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """Enforces server-side authorization check for administrative operations.
    
    Rejects ordinary authenticated users with 403 Forbidden.
    """
    if not user.is_admin:
        raise ForbiddenException("Administrator privileges required for this action")
    return user
