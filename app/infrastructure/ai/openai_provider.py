"""Adapter OpenAI para classificação estruturada e sem ações autônomas."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar

import openai
from openai import AsyncOpenAI
from pydantic import ValidationError
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, wait_exponential

from app.core.exceptions import ExternalServiceError
from app.domain.entities.classification_candidate import ClassificationCandidate
from app.domain.entities.email_message import EmailMessage
from app.infrastructure.ai.prompt import SYSTEM_RULES, build_untrusted_email_input
from app.infrastructure.ai.schemas import AIEmailClassificationOutput

T = TypeVar("T")
_RECOVERABLE_STATUS = {408, 409, 429, 500, 502, 503, 504}


def _is_recoverable(exc: BaseException) -> bool:
    """Limita retries a indisponibilidade, timeout, rate limit e erros 5xx."""

    if isinstance(exc, (openai.APIConnectionError, openai.APITimeoutError)):
        return True
    if isinstance(exc, openai.APIStatusError):
        return exc.status_code in _RECOVERABLE_STATUS
    return False


class OpenAIEmailClassifier:
    """Implementa AIProvider usando Responses API e validação Pydantic."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        prompt_version: str,
        timeout_seconds: float,
        retry_attempts: int,
        max_input_characters: int,
        client: AsyncOpenAI | None = None,
    ) -> None:
        self._model = model
        self._prompt_version = prompt_version
        self._retry_attempts = retry_attempts
        self._max_input_characters = max_input_characters
        self._client = client or AsyncOpenAI(
            api_key=api_key,
            timeout=timeout_seconds,
            max_retries=0,
        )

    @property
    def model_name(self) -> str:
        """Retorna o modelo configurado sem expor credenciais."""

        return self._model

    @property
    def prompt_version(self) -> str:
        """Retorna a versão persistida junto à classificação."""

        return self._prompt_version

    async def _retry(self, operation: Callable[[], Awaitable[T]]) -> T:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(self._retry_attempts),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
            retry=retry_if_exception(_is_recoverable),
            reraise=True,
        ):
            with attempt:
                return await operation()
        raise RuntimeError("Fluxo de retry terminou sem resultado.")  # pragma: no cover

    async def classify_email(self, email: EmailMessage) -> ClassificationCandidate:
        """Solicita saída estruturada e converte o schema para o domínio."""

        async def request() -> object:
            return await self._client.responses.parse(
                model=self._model,
                instructions=SYSTEM_RULES,
                input=build_untrusted_email_input(
                    email,
                    max_characters=self._max_input_characters,
                ),
                text_format=AIEmailClassificationOutput,
                store=False,
            )

        try:
            response = await self._retry(request)
            parsed = getattr(response, "output_parsed", None)
            if not isinstance(parsed, AIEmailClassificationOutput):
                raise ValueError("O provedor não retornou classificação estruturada.")
        except (openai.APIError, ValidationError, ValueError, TypeError) as exc:
            raise ExternalServiceError("OpenAI") from exc

        return ClassificationCandidate(
            category=parsed.category,
            priority=parsed.priority,
            requires_reply=parsed.requires_reply,
            confidence=parsed.confidence,
            summary=parsed.summary,
            reason=parsed.reason,
            risk_flags=tuple(parsed.risk_flags),
        )
