"""
Endpoints for conversation and message management with SQLite persistence.
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.services.session_service import SessionService, get_session_service

router = APIRouter(prefix="/conversations", tags=["Conversations"])


class CreateConversationRequest(BaseModel):
    title: Optional[str] = Field(default="New Chat", description="Initial conversation title")


class RenameConversationRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=100, description="New conversation title")


class ConversationItem(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int = 0


class MessageItem(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    sources: List[str] = Field(default_factory=list)
    tools_used: List[str] = Field(default_factory=list)
    created_at: str


class ConversationDetailResponse(BaseModel):
    conversation: ConversationItem
    messages: List[MessageItem]


@router.post(
    "",
    response_model=ConversationItem,
    status_code=status.HTTP_201_CREATED,
    summary="Create Conversation",
)
async def create_conversation(
    req: CreateConversationRequest,
    session_service: SessionService = Depends(get_session_service),
) -> ConversationItem:
    res = await run_in_threadpool(session_service.create_conversation, title=req.title or "New Chat")
    return ConversationItem(**res)


@router.get(
    "",
    response_model=List[ConversationItem],
    status_code=status.HTTP_200_OK,
    summary="List Conversations",
)
async def list_conversations(
    session_service: SessionService = Depends(get_session_service),
) -> List[ConversationItem]:
    res = await run_in_threadpool(session_service.list_conversations)
    return [ConversationItem(**item) for item in res]


@router.get(
    "/{conv_id}",
    response_model=ConversationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Conversation Detail and Messages",
)
async def get_conversation(
    conv_id: str,
    session_service: SessionService = Depends(get_session_service),
) -> ConversationDetailResponse:
    conv = await run_in_threadpool(session_service.get_conversation, conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = await run_in_threadpool(session_service.get_messages, conv_id)
    conv_item = ConversationItem(
        id=conv["id"],
        title=conv["title"],
        created_at=conv["created_at"],
        updated_at=conv["updated_at"],
        message_count=len(messages),
    )
    return ConversationDetailResponse(
        conversation=conv_item,
        messages=[MessageItem(**m) for m in messages],
    )


@router.patch(
    "/{conv_id}",
    status_code=status.HTTP_200_OK,
    summary="Rename Conversation",
)
async def rename_conversation(
    conv_id: str,
    req: RenameConversationRequest,
    session_service: SessionService = Depends(get_session_service),
):
    success = await run_in_threadpool(session_service.rename_conversation, conv_id, req.title)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"success": True, "title": req.title}


@router.delete(
    "/{conv_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Conversation",
)
async def delete_conversation(
    conv_id: str,
    session_service: SessionService = Depends(get_session_service),
):
    success = await run_in_threadpool(session_service.delete_conversation, conv_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"success": True, "deleted": conv_id}


@router.delete(
    "/{conv_id}/messages",
    status_code=status.HTTP_200_OK,
    summary="Clear Conversation History",
)
async def clear_messages(
    conv_id: str,
    session_service: SessionService = Depends(get_session_service),
):
    success = await run_in_threadpool(session_service.clear_history, conv_id)
    return {"success": True, "cleared": conv_id}
