from fastapi import APIRouter
from ..core.config import settings
from ..schemas.common import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Service health check endpoint."""
    return HealthResponse(
        status="ok",
        service="flashfit-api",
        environment=settings.ENVIRONMENT,
        version=settings.VERSION,
    )
