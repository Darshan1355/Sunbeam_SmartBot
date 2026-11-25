"""
Endpoints for inspecting available LangChain callable tools and their capabilities.
"""
from fastapi import APIRouter, Depends, status

from app.schemas.tools import ToolListResponse
from app.tools.registry import ToolRegistry, get_tool_registry

router = APIRouter(prefix="/tools", tags=["Agent Tools"])


@router.get(
    "",
    response_model=ToolListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Registered Agent Tools",
    description="Returns metadata, descriptions, categories, and availability for all callable LangChain tools.",
)
async def list_available_tools(
    registry: ToolRegistry = Depends(get_tool_registry),
) -> ToolListResponse:
    tool_infos = registry.get_tool_infos()
    return ToolListResponse(
        total_tools=len(tool_infos),
        tools=tool_infos,
    )
