"""Testes do adapter Groq sem chamadas externas."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.domain.entities.email_message import EmailMessage
from app.domain.enums.email_category import EmailCategory
from app.infrastructure.ai.groq_provider import GroqEmailClassifier
from app.infrastructure.ai.schemas import AIEmailClassificationOutput


class FakeResponses:
    """Simula a Responses API sem comunicação de rede."""

    def __init__(self) -> None:
        self.kwargs: dict[str, object] = {}

    async def parse(
        self,
        **kwargs: object,
    ) -> object:
        self.kwargs = kwargs

        return SimpleNamespace(
            output_parsed=AIEmailClassificationOutput(
                category="trabalho",
                priority="high",
                requires_reply=True,
                confidence=0.93,
                summary="Resumo estruturado.",
                reason="Mensagem relacionada a projeto.",
                risk_flags=[],
            )
        )


@pytest.mark.asyncio
async def test_groq_uses_structured_output_without_store() -> None:
    """Valida schema, entrada não confiável e ausência de `store`."""

    responses = FakeResponses()
    client = SimpleNamespace(responses=responses)

    provider = GroqEmailClassifier(
        api_key="test-key",
        base_url="https://api.groq.test/openai/v1",
        model="openai/gpt-oss-20b",
        prompt_version="test-v1",
        timeout_seconds=5,
        retry_attempts=1,
        max_input_characters=5000,
        client=client,  # type: ignore[arg-type]
    )

    email = EmailMessage(
        provider_message_id="message-id",
        provider_thread_id="thread-id",
        sender="cliente@example.com",
        recipients=("usuario@example.com",),
        subject="Projeto",
        received_at=datetime.now(UTC),
        snippet="Preciso de retorno sobre o relatório.",
        body_hash="a" * 64,
    )

    result = await provider.classify_email(email)

    assert result.category is EmailCategory.WORK
    assert responses.kwargs["text_format"] is AIEmailClassificationOutput
    assert "UNTRUSTED EMAIL CONTENT" in str(responses.kwargs["input"])
    assert "store" not in responses.kwargs
