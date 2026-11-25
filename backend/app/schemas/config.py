from typing import List
from pydantic import BaseModel, Field


class PublicConfigResponse(BaseModel):
    """
    Public configuration safely exposed to frontend clients.
    NEVER includes API keys, tokens, or private secrets.
    """
    app_name: str
    version: str
    environment: str
    groq_model: str = Field(..., description="Active LLM model used for inference")
    allowed_origins: List[str]
    features: List[str] = Field(
        default_factory=lambda: [
            "health_checks",
            "groq_integration",
            "agentic_rag_ready",
            "sse_streaming_ready",
        ]
    )
