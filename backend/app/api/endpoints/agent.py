"""
Endpoints for executing inquiries through the LangGraph Agentic RAG system.
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.agent.agent_service import AgentExecutionResult, AgentService, get_agent_service

router = APIRouter(prefix="/agent", tags=["Agentic RAG"])


class AgentChatRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User question or inquiry")
    history: Optional[List[Dict[str, str]]] = Field(
        default=None, description="Previous conversation turns [{'role': 'user', 'content': '...'}, ...]"
    )
    max_retries: int = Field(default=1, ge=0, le=3, description="Maximum retrieval rewrite retries")


@router.post(
    "/chat",
    response_model=AgentExecutionResult,
    status_code=status.HTTP_200_OK,
    summary="Execute Agentic RAG Chat Query",
    description="Orchestrates query understanding, dynamic tool selection, multi-step retrieval, relevance evaluation, and grounded answer synthesis via LangGraph.",
)
async def execute_agent_chat(
    req: AgentChatRequest,
    agent_service: AgentService = Depends(get_agent_service),
) -> AgentExecutionResult:
    return await agent_service.execute(
        query=req.query,
        history=req.history,
        max_retries=req.max_retries,
    )
