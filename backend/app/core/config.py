import os
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env.local", ".env.local", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General App Config
    PROJECT_NAME: str = "StyleSense API"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # CORS configuration - default allows Vite dev origin (5173) and Next.js dev origins (3000/3001)
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]

    # Supabase Configuration
    # Fallback to NEXT_PUBLIC_* if SUPABASE_* is not explicitly set in environment
    SUPABASE_URL: str = Field(
        default_factory=lambda: os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL", "")
    )
    SUPABASE_ANON_KEY: str = Field(
        default_factory=lambda: os.getenv("SUPABASE_ANON_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "")
    )
    SUPABASE_SERVICE_ROLE_KEY: str = Field(
        default_factory=lambda: os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    )
    SUPABASE_JWT_SECRET: Optional[str] = None

    # Server-side admin authorization allowlists (backed by server configuration)
    ADMIN_EMAILS: List[str] = Field(default_factory=list)
    ADMIN_USER_IDS: List[str] = Field(default_factory=list)

    # OpenRouter AI Configuration (Optional server-side provider)
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_MODEL: str = "nvidia/nemotron-3.5-lightning:free"

    # Site URL
    SITE_URL: str = Field(
        default_factory=lambda: os.getenv("SITE_URL") or os.getenv("NEXT_PUBLIC_SITE_URL", "http://localhost:5173")
    )

    @field_validator("CORS_ORIGINS", "ADMIN_EMAILS", "ADMIN_USER_IDS", mode="before")
    @classmethod
    def assemble_string_list(cls, v):
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, tuple)):
            return list(v)
        return []


settings = Settings()
