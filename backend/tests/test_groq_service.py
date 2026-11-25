import pytest
from app.core.config import Settings
from app.services.groq_service import GroqService
from app.schemas.chat import ChatMessage


def test_groq_service_configuration():
    service = GroqService()
    assert service.is_configured is True
    assert service._default_model == "openai/gpt-oss-120b"
    assert service._timeout == 30.0


def test_groq_service_placeholder_key():
    custom_settings = Settings(GROQ_API_KEY="your_groq_api_key_here")
    service = GroqService(settings=custom_settings)
    assert service.is_configured is False
