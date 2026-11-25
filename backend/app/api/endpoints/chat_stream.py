"""
Server-Sent Events (SSE) streaming endpoint for real-time Agentic RAG chat.
Streams status updates, tool executions, live LLM tokens, sources, and saves to SQLite.
"""
import asyncio
import json
import uuid
from typing import AsyncGenerator, Dict, List, Optional
from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse
from starlette.concurrency import run_in_threadpool

from app.agent.nodes import analyze_intent_node, tool_execution_node
from app.agent.prompts import (
    DIRECT_GENERATOR_SYSTEM_PROMPT,
    GROUNDED_GENERATOR_SYSTEM_PROMPT,
    GROUNDED_GENERATOR_USER_PROMPT,
)
from app.agent.state import AgentState
from app.core.logging import get_logger
from app.schemas.chat import ChatMessage
from app.services.groq_service import GroqService, get_groq_service
from app.services.session_service import SessionService, get_session_service

logger = get_logger("app.api.chat_stream")
router = APIRouter(prefix="/chat", tags=["Streaming Chat"])


class StreamChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User's query")
    conversation_id: Optional[str] = Field(
        default=None, description="Existing conversation UUID, or empty to create new"
    )


async def sse_event_generator(
    req: StreamChatRequest,
    http_request: Request,
    session_service: SessionService,
    groq_service: GroqService,
) -> AsyncGenerator[Dict[str, str], None]:
    conv_id = req.conversation_id or str(uuid.uuid4())
    user_query = req.message.strip()

    # 1. Save user message to persistent SQLite
    try:
        await run_in_threadpool(
            session_service.save_message,
            conv_id=conv_id,
            role="user",
            content=user_query,
        )
    except Exception as e:
        logger.warning(f"Could not save user message: {e}")

    # Fetch recent history for context
    history = []
    try:
        history = await run_in_threadpool(session_service.get_messages, conv_id)
    except Exception:
        pass

    state: AgentState = {
        "query": user_query,
        "history": history,
        "intent": "general_rag",
        "requires_rag": True,
        "rewritten_query": user_query,
        "selected_tools": [],
        "tool_results": {},
        "tool_activity": [],
        "retrieved_context": [],
        "sources": [],
        "retrieval_relevance": 0.0,
        "relevance_reason": "",
        "retry_count": 0,
        "max_retries": 1,
        "final_answer": "",
    }

    try:
        # Event 1: Status
        yield {
            "event": "status",
            "data": json.dumps({"message": "Understanding your question...", "conversation_id": conv_id}),
        }

        # Step 1: Analyze Intent
        intent_res = await analyze_intent_node(state)
        state.update(intent_res)

        if await http_request.is_disconnected():
            logger.info("Client disconnected during intent analysis.")
            return

        requires_rag = state.get("requires_rag", True)
        selected_tools = state.get("selected_tools", [])

        if requires_rag and selected_tools:
            # Event: Tool status
            for tool_name in selected_tools:
                yield {
                    "event": "tool",
                    "data": json.dumps({
                        "tool": tool_name,
                        "status": "running",
                        "message": f"Executing {tool_name.replace('_', ' ').title()}...",
                    }),
                }

            # Step 2: Tool Execution
            tool_res = await tool_execution_node(state)
            state.update(tool_res)

            for tool_name in selected_tools:
                yield {
                    "event": "tool",
                    "data": json.dumps({
                        "tool": tool_name,
                        "status": "completed",
                        "message": f"Completed {tool_name.replace('_', ' ').title()}",
                    }),
                }

            if await http_request.is_disconnected():
                logger.info("Client disconnected during tool execution.")
                return

            # Yield Sources event
            sources = state.get("sources", [])
            if sources:
                yield {
                    "event": "sources",
                    "data": json.dumps({"sources": sources}),
                }

        # Event: Status (Generating Answer)
        yield {
            "event": "status",
            "data": json.dumps({"message": "Synthesizing response..."}),
        }

        # Step 3: Stream Tokens directly from Groq
        full_assistant_reply = []

        if not requires_rag:
            # Direct general coding / greeting question
            messages = [
                ChatMessage(role="system", content=DIRECT_GENERATOR_SYSTEM_PROMPT),
                ChatMessage(role="user", content=user_query),
            ]
        else:
            context_list = state.get("retrieved_context", [])
            compiled_context = "\n\n---\n\n".join(context_list[:5])
            if not compiled_context.strip():
                default_msg = "I don't have enough information in the Sunbeam records to answer that question accurately."
                yield {"event": "token", "data": json.dumps({"content": default_msg})}
                full_assistant_reply.append(default_msg)
                messages = []
            else:
                active_question = state.get("rewritten_query") or user_query
                user_prompt = GROUNDED_GENERATOR_USER_PROMPT.format(
                    question=active_question,
                    context=compiled_context,
                )
                messages = [
                    ChatMessage(role="system", content=GROUNDED_GENERATOR_SYSTEM_PROMPT),
                    ChatMessage(role="user", content=user_prompt),
                ]

        if messages:
            async for token_chunk in groq_service.stream_chat(messages=messages):
                if await http_request.is_disconnected():
                    logger.info("Client disconnected during token streaming.")
                    break
                full_assistant_reply.append(token_chunk)
                yield {
                    "event": "token",
                    "data": json.dumps({"content": token_chunk}),
                }

        final_content = "".join(full_assistant_reply)

        # 4. Save assistant response to persistent SQLite
        saved_msg = await run_in_threadpool(
            session_service.save_message,
            conv_id=conv_id,
            role="assistant",
            content=final_content,
            sources=state.get("sources", []),
            tools_used=state.get("selected_tools", []),
        )

        # Event: Done
        yield {
            "event": "done",
            "data": json.dumps({
                "status": "completed",
                "conversation_id": conv_id,
                "message_id": saved_msg["id"],
                "sources": state.get("sources", []),
                "tools_used": state.get("selected_tools", []),
            }),
        }

    except Exception as e:
        logger.exception(f"Error during chat stream: {str(e)}")
        yield {
            "event": "error",
            "data": json.dumps({"error": str(e), "conversation_id": conv_id}),
        }


@router.post(
    "/stream",
    summary="Real-time Server-Sent Events Chat Stream",
    description="Streams status updates, tool invocations, live tokens, and source metadata via SSE.",
)
async def stream_chat_endpoint(
    req: StreamChatRequest,
    request: Request,
    session_service: SessionService = Depends(get_session_service),
    groq_service: GroqService = Depends(get_groq_service),
):
    return EventSourceResponse(
        sse_event_generator(req, request, session_service, groq_service)
    )
