from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import get_logger, setup_logging

settings = get_settings()
setup_logging(debug=settings.DEBUG)
logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI Lifespan management for startup and shutdown procedures.
    """
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} [{settings.ENVIRONMENT}]")
    logger.info(f"CORS allowed origins: {settings.CORS_ORIGINS}")
    logger.info(f"Default Groq model configured: {settings.GROQ_MODEL}")

    # Check key presence on startup without leaking
    key_preview = settings.GROQ_API_KEY.get_secret_value()
    if key_preview and not key_preview.startswith("your_"):
        masked = key_preview[:4] + "..." + key_preview[-4:] if len(key_preview) > 8 else "***"
        logger.info(f"Groq API key loaded successfully (Key: {masked})")
    else:
        logger.warning("Groq API key is NOT configured or is set to placeholder! Set GROQ_API_KEY in .env")

    yield

    logger.info(f"Shutting down {settings.APP_NAME}...")


def create_app() -> FastAPI:
    """
    Application factory pattern initializing FastAPI with middlewares,
    routers, centralized error handling, and optional static frontend distribution.
    """
    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Backend API service for Sunbeam SmartBot with Groq LLM integration and Agentic RAG.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # 1. Register CORS Middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Register Centralized Exception Handlers
    register_exception_handlers(application)

    # 3. Mount API Routers
    application.include_router(api_router)

    # 4. Mount Production Frontend Distribution if built
    dist_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    if dist_path.exists() and (dist_path / "index.html").exists():
        logger.info(f"Mounting production frontend build from {dist_path}")
        application.mount("/", StaticFiles(directory=str(dist_path), html=True), name="frontend")
    else:
        # Fallback root greeting
        @application.get("/", tags=["Root"])
        async def root():
            return JSONResponse(
                content={
                    "name": settings.APP_NAME,
                    "version": settings.APP_VERSION,
                    "environment": settings.ENVIRONMENT,
                    "docs": "/docs",
                    "health": "/api/health",
                    "config": "/api/config",
                }
            )

    return application


app = create_app()
