from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ToolInfo(BaseModel):
    name: str
    description: str
    category: str
    is_available: bool = True
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ToolListResponse(BaseModel):
    total_tools: int
    tools: List[ToolInfo]


class ToolExecutionLog(BaseModel):
    tool_name: str
    input_args: Dict[str, Any]
    output_preview: str
    latency_ms: float
    status: str
