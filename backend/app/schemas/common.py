from typing import Any, Optional
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error description")
    details: Optional[Any] = Field(None, description="Additional context or validation details")


class ErrorResponse(BaseModel):
    error: ErrorDetail


class HealthResponse(BaseModel):
    status: str = Field("ok", description="Health status string")
    service: str = Field("flashfit-api", description="Service identifier")
    environment: str = Field(..., description="Deployment environment")
    version: str = Field(..., description="Application version")
