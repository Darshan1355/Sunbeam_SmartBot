import json
from functools import lru_cache
from pathlib import Path
from typing import List, Union

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = PROJECT_ROOT / "backend"


class Settings(BaseSettings):
    """
    Centralized application configuration loaded from environment variables
    and .env files.
    """

    # Server Configuration
    APP_NAME: str = "Sunbeam SmartBot API"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development", description="Current environment: development, staging, production")
    DEBUG: bool = Field(default=False, description="Enable FastAPI debug mode")
    HOST: str = Field(default="0.0.0.0", description="Host to bind server")
    PORT: int = Field(default=8000, description="Port to bind server")

    # CORS Configuration
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["*"]

    # Groq API Configuration
    GROQ_API_KEY: SecretStr = Field(
        default=SecretStr(""),
        description="Groq API key for LLM orchestration (never exposed to clients)",
    )
    GROQ_MODEL: str = Field(
        default="openai/gpt-oss-120b",
        description="Default Groq LLM model identifier",
    )
    GROQ_TIMEOUT_SECONDS: float = Field(
        default=30.0,
        description="Timeout for Groq API calls in seconds",
    )
    GROQ_MAX_RETRIES: int = Field(
        default=2,
        description="Maximum automatic retries on Groq API connection failures",
    )
    GROQ_TEMPERATURE: float = Field(
        default=0.1,
        description="Sampling temperature for LLM completions",
    )

    # Vector Database & Storage Paths
    CHROMA_PERSIST_DIR: str = Field(
        default=str(PROJECT_ROOT / "data" / "chroma_db"),
        description="Path to persisted ChromaDB vector database directory",
    )

    # Pydantic Settings Configuration
    model_config = SettingsConfigDict(
        env_file=(
            str(BACKEND_ROOT / ".env"),
            str(PROJECT_ROOT / ".env"),
            ".env",
        ),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Cached accessor for application settings.
    """
    return Settings()
