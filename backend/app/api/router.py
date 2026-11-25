from fastapi import APIRouter

from app.api.endpoints.health import router as health_router
from app.api.endpoints.config import router as config_router
from app.api.endpoints.chat import router as chat_router
from app.api.endpoints.chat_stream import router as chat_stream_router
from app.api.endpoints.conversations import router as conversations_router
from app.api.endpoints.knowledge_base import router as knowledge_router
from app.api.endpoints.tools import router as tools_router
from app.api.endpoints.agent import router as agent_router

api_router = APIRouter(prefix="/api")

api_router.include_router(health_router)
api_router.include_router(config_router)
api_router.include_router(chat_router)
api_router.include_router(chat_stream_router)
api_router.include_router(conversations_router)
api_router.include_router(knowledge_router)
api_router.include_router(tools_router)
api_router.include_router(agent_router)
