"""Pydantic schemas for style profiles and user consents."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# -----------------------------------------------------------------------
# Valid body type labels — self-selected, neutral descriptions
# -----------------------------------------------------------------------
VALID_BODY_TYPES = {
    "Hourglass",
    "Pear",
    "Rectangle",
    "Inverted Triangle",
    "Apple",
}

# -----------------------------------------------------------------------
# Style Profile
# -----------------------------------------------------------------------


class StyleProfileBase(BaseModel):
    """Fields that a user can read and write on their own profile."""

    favorite_styles: List[str] = Field(
        default_factory=list,
        max_length=20,
        description="Preferred style archetypes, e.g. 'minimal', 'classic', 'traditional'",
    )
    favorite_colors: List[str] = Field(
        default_factory=list,
        max_length=30,
        description="Preferred colour names or hex codes",
    )
    budget_min: Optional[int] = Field(
        None,
        ge=0,
        description="Minimum budget in price_cents (INR × 100). Null = no lower bound.",
    )
    budget_max: Optional[int] = Field(
        None,
        ge=0,
        description="Maximum budget in price_cents (INR × 100). Null = no upper bound.",
    )
    occasions: List[str] = Field(
        default_factory=list,
        max_length=20,
        description="Preferred occasions, e.g. 'casual', 'work', 'festive', 'wedding'",
    )
    body_type: Optional[str] = Field(
        None,
        description="Self-selected body shape label. One of: Hourglass, Pear, Rectangle, Inverted Triangle, Apple. Null = skip.",
    )
    onboarding_complete: bool = Field(
        False,
        description="Whether the user has finished the onboarding flow.",
    )

    @field_validator("body_type", mode="before")
    @classmethod
    def validate_body_type(cls, v: Any) -> Optional[str]:
        if v is None or v == "":
            return None
        v_str = str(v).strip()
        if v_str not in VALID_BODY_TYPES:
            raise ValueError(
                f"Invalid body_type '{v_str}'. Must be one of: {', '.join(sorted(VALID_BODY_TYPES))}"
            )
        return v_str

    @field_validator("budget_min", "budget_max", mode="before")
    @classmethod
    def coerce_budget(cls, v: Any) -> Optional[int]:
        if v is None or v == "" or v == "null":
            return None
        return int(v)


class StyleProfileUpdate(StyleProfileBase):
    """PUT body for creating/updating a style profile."""

    pass


class StyleProfileResponse(StyleProfileBase):
    """Returned when reading a user's profile."""

    user_id: str
    body_guidance: Optional[Dict[str, Any]] = Field(
        None,
        description="Derived body-fit guidance (not raw measurements). Null when consent is absent or guidance not computed.",
    )
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# -----------------------------------------------------------------------
# User Consents
# -----------------------------------------------------------------------

VALID_CONSENT_TYPES = {
    "body_guidance_storage",
}


class ConsentGrant(BaseModel):
    """Body for granting or revoking a single consent."""

    consent_type: str = Field(
        ...,
        description="Type of consent, e.g. 'body_guidance_storage'.",
    )
    granted: bool = Field(
        ...,
        description="True to grant, False to revoke.",
    )

    @field_validator("consent_type", mode="before")
    @classmethod
    def validate_consent_type(cls, v: Any) -> str:
        v_str = str(v).strip()
        if v_str not in VALID_CONSENT_TYPES:
            raise ValueError(
                f"Unknown consent_type '{v_str}'. Must be one of: {', '.join(sorted(VALID_CONSENT_TYPES))}"
            )
        return v_str


class ConsentResponse(BaseModel):
    """Returned when reading a consent record."""

    consent_type: str
    granted: bool
    granted_at: Optional[str] = None
    revoked_at: Optional[str] = None


class ConsentListResponse(BaseModel):
    """Wrapper for listing all user consents."""

    consents: List[ConsentResponse]
