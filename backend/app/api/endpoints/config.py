from fastapi import APIRouter, Depends, status

from app.core.config import Settings, get_settings
from app.schemas.config import PublicConfigResponse

router = APIRouter(prefix="/config", tags=["Configuration"])


@router.get(
    "",
    response_model=PublicConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Safe Public Client Configuration",
    description="Returns public application settings, active LLM model identifier, and supported capabilities. Strictly omits secret credentials.",
)
async def get_public_config(
    settings: Settings = Depends(get_settings),
) -> PublicConfigResponse:
    return PublicConfigResponse(
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        groq_model=settings.GROQ_MODEL,
        allowed_origins=settings.CORS_ORIGINS,
    )
