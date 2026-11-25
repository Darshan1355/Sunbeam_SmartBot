from datetime import datetime, timezone
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ServiceComponentStatus(BaseModel):
    name: str = Field(..., description="Service component name (e.g. groq, chromadb)")
    status: str = Field(..., description="'healthy', 'degraded', or 'unhealthy'")
    latency_ms: Optional[float] = Field(default=None, description="Check latency in milliseconds")
    details: Dict[str, str] = Field(default_factory=dict, description="Diagnostic details")


class HealthResponse(BaseModel):
    status: str = Field(default="healthy", description="Overall system health status")
    app_name: str
    version: str
    environment: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    components: List[ServiceComponentStatus] = Field(default_factory=list)
