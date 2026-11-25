from fastapi import APIRouter, Depends, status

from app.schemas.chat import ChatCompletionRequest, ChatCompletionResponse
from app.services.groq_service import GroqService, get_groq_service

router = APIRouter(prefix="/chat", tags=["Chat & Completions"])


@router.post(
    "/completions",
    response_model=ChatCompletionResponse,
    status_code=status.HTTP_200_OK,
    summary="Create Chat Completion via Groq",
    description="Direct completion endpoint using configured Groq LLM service. Validates connection and model responsiveness.",
)
async def create_chat_completion(
    request: ChatCompletionRequest,
    groq_service: GroqService = Depends(get_groq_service),
) -> ChatCompletionResponse:
    return await groq_service.generate_chat(
        messages=request.messages,
        model=request.model,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )
