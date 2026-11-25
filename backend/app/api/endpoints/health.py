from fastapi import APIRouter, Depends, status

from app.core.config import Settings, get_settings
from app.schemas.health import HealthResponse
from app.services.groq_service import GroqService, get_groq_service

router = APIRouter(prefix="/health", tags=["Health & Diagnostics"])


@router.get(
    "",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="System and Component Health Check",
    description="Returns high-level API status and diagnostic checks for integrated services like Groq.",
)
async def get_system_health(
    settings: Settings = Depends(get_settings),
    groq_service: GroqService = Depends(get_groq_service),
) -> HealthResponse:
    # Run Groq health check
    groq_status = await groq_service.check_health()

    components = [groq_status]

    # Calculate overall status
    overall_status = "healthy"
    if any(c.status == "unhealthy" for c in components):
        overall_status = "degraded" if groq_status.status != "unhealthy" else "unhealthy"
    elif any(c.status == "degraded" for c in components):
        overall_status = "degraded"

    return HealthResponse(
        status=overall_status,
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        components=components,
    )
