import asyncio
import time
from typing import AsyncIterator, List, Optional

from groq import AsyncGroq, Groq
from groq import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
)

from app.core.config import Settings, get_settings
from app.core.errors import (
    ConfigurationError,
    GroqRateLimitError,
    GroqServiceError,
    GroqTimeoutError,
)
from app.core.logging import get_logger
from app.schemas.chat import (
    ChatCompletionResponse,
    ChatMessage,
    TokenUsage,
)
from app.schemas.health import ServiceComponentStatus

logger = get_logger("app.services.groq")


class GroqService:
    """
    Production-ready reusable Groq API service.
    Handles client initialization, model configuration, rate limiting,
    timeouts, and async completions and streaming.
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self._api_key = self.settings.GROQ_API_KEY.get_secret_value()
        self._default_model = self.settings.GROQ_MODEL
        self._timeout = self.settings.GROQ_TIMEOUT_SECONDS
        self._max_retries = self.settings.GROQ_MAX_RETRIES

        self._sync_client: Optional[Groq] = None
        self._async_client: Optional[AsyncGroq] = None

    @property
    def is_configured(self) -> bool:
        """Checks whether a valid API key is present."""
        return bool(self._api_key and self._api_key.strip() and not self._api_key.startswith("your_"))

    def _get_async_client(self) -> AsyncGroq:
        """Initializes and returns the AsyncGroq client."""
        if not self.is_configured:
            raise ConfigurationError(
                message="GROQ_API_KEY is not configured or is invalid. Set GROQ_API_KEY in your .env file."
            )
        if self._async_client is None:
            self._async_client = AsyncGroq(
                api_key=self._api_key,
                timeout=self._timeout,
                max_retries=self._max_retries,
            )
        return self._async_client

    def _get_sync_client(self) -> Groq:
        """Initializes and returns the synchronous Groq client."""
        if not self.is_configured:
            raise ConfigurationError(
                message="GROQ_API_KEY is not configured or is invalid. Set GROQ_API_KEY in your .env file."
            )
        if self._sync_client is None:
            self._sync_client = Groq(
                api_key=self._api_key,
                timeout=self._timeout,
                max_retries=self._max_retries,
            )
        return self._sync_client

    async def check_health(self) -> ServiceComponentStatus:
        """
        Validates Groq connectivity, authentication, and reports round-trip latency.
        """
        if not self.is_configured:
            return ServiceComponentStatus(
                name="groq",
                status="unhealthy",
                details={"reason": "GROQ_API_KEY is missing or using placeholder value"},
            )

        start_time = time.perf_counter()
        try:
            client = self._get_async_client()
            # Fetch model list as a low-overhead health check
            models_response = await client.models.list()
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            available_model_ids = [m.id for m in models_response.data]
            model_found = self._default_model in available_model_ids

            return ServiceComponentStatus(
                name="groq",
                status="healthy" if model_found else "degraded",
                latency_ms=latency_ms,
                details={
                    "configured_model": self._default_model,
                    "model_available": str(model_found),
                    "total_models": str(len(available_model_ids)),
                },
            )
        except AuthenticationError as e:
            return ServiceComponentStatus(
                name="groq",
                status="unhealthy",
                latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
                details={"error": "Authentication failed - invalid GROQ_API_KEY", "code": str(e.status_code)},
            )
        except (APITimeoutError, asyncio.TimeoutError):
            return ServiceComponentStatus(
                name="groq",
                status="unhealthy",
                latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
                details={"error": f"Connection timed out after {self._timeout}s"},
            )
        except Exception as e:
            logger.warning(f"Groq health check encountered issue: {str(e)}")
            return ServiceComponentStatus(
                name="groq",
                status="unhealthy",
                latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
                details={"error": str(e)},
            )

    async def generate_chat(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> ChatCompletionResponse:
        """
        Executes an asynchronous chat completion with error translation and latency tracking.
        """
        client = self._get_async_client()
        active_model = model or self._default_model
        active_temp = temperature if temperature is not None else self.settings.GROQ_TEMPERATURE

        formatted_messages = [{"role": m.role, "content": m.content} for m in messages]

        start_time = time.perf_counter()
        try:
            kwargs = {
                "model": active_model,
                "messages": formatted_messages,
                "temperature": active_temp,
            }
            if max_tokens:
                kwargs["max_tokens"] = max_tokens

            response = await client.chat.completions.create(**kwargs)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            choice = response.choices[0]
            content = choice.message.content or ""

            usage = None
            if response.usage:
                usage = TokenUsage(
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                )

            return ChatCompletionResponse(
                id=response.id,
                model=response.model,
                content=content,
                finish_reason=choice.finish_reason,
                usage=usage,
                latency_ms=latency_ms,
            )

        except RateLimitError as e:
            logger.error(f"Groq rate limit exceeded: {str(e)}")
            raise GroqRateLimitError(
                message="Groq API rate limit reached. Please try again shortly.",
                details={"model": active_model, "raw_error": str(e)},
            )
        except (APITimeoutError, asyncio.TimeoutError) as e:
            logger.error(f"Groq API call timed out after {self._timeout}s: {str(e)}")
            raise GroqTimeoutError(
                message=f"Groq request timed out after {self._timeout} seconds",
                details={"model": active_model},
            )
        except APIStatusError as e:
            logger.error(f"Groq API status error ({e.status_code}): {e.message}")
            raise GroqServiceError(
                message=f"Groq API error ({e.status_code}): {e.message}",
                status_code=e.status_code if e.status_code < 500 else 502,
                details={"model": active_model, "code": e.code},
            )
        except APIConnectionError as e:
            logger.error(f"Failed to connect to Groq API: {str(e)}")
            raise GroqServiceError(
                message="Failed to establish connection to Groq API",
                status_code=503,
                details={"model": active_model, "error": str(e)},
            )
        except Exception as e:
            logger.exception(f"Unexpected error during Groq chat completion: {str(e)}")
            raise GroqServiceError(
                message=f"Groq service error: {str(e)}",
                details={"model": active_model},
            )

    async def stream_chat(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """
        Asynchronously streams completion tokens from Groq.
        """
        client = self._get_async_client()
        active_model = model or self._default_model
        active_temp = temperature if temperature is not None else self.settings.GROQ_TEMPERATURE

        formatted_messages = [{"role": m.role, "content": m.content} for m in messages]

        try:
            kwargs = {
                "model": active_model,
                "messages": formatted_messages,
                "temperature": active_temp,
                "stream": True,
            }
            if max_tokens:
                kwargs["max_tokens"] = max_tokens

            stream = await client.chat.completions.create(**kwargs)
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except RateLimitError as e:
            logger.error(f"Groq stream rate limit: {str(e)}")
            raise GroqRateLimitError(message="Groq stream rate limited", details={"model": active_model})
        except Exception as e:
            logger.exception(f"Error streaming from Groq: {str(e)}")
            raise GroqServiceError(message=f"Groq stream error: {str(e)}")


_groq_service_instance: Optional[GroqService] = None


def get_groq_service() -> GroqService:
    """Dependency injection provider for GroqService singleton."""
    global _groq_service_instance
    if _groq_service_instance is None:
        _groq_service_instance = GroqService()
    return _groq_service_instance
