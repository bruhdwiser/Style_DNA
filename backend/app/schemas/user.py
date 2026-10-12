from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class AuthenticatedUser(BaseModel):
    id: str = Field(..., description="Supabase Auth UUID")
    email: Optional[str] = Field(None, description="User email address")
    role: Optional[str] = Field("authenticated", description="Supabase user role")
    is_admin: bool = Field(False, description="Whether user has verified admin privileges")
    app_metadata: Dict[str, Any] = Field(default_factory=dict)
    user_metadata: Dict[str, Any] = Field(default_factory=dict)


class CurrentUserResponse(BaseModel):
    user: AuthenticatedUser
