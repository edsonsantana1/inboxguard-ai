"""Testes do adapter OpenAI sem chamada de rede."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.domain.entities.email_message import EmailMessage
from app.domain.enums.email_category import EmailCategory
from app.infrastructure.ai.openai_provider import OpenAIEmailClassifier
from app.infrastructure.ai.schemas import AIEmailClassificationOutput


class FakeResponses:
    def __init__(self) -> None:
        self.kwargs: dict[str, object] = {}

    async def parse(self, **kwargs: object) -> object:
        self.kwargs = kwargs
        return SimpleNamespace(
            output_parsed=AIEmailClassificationOutput(
                category="trabalho",
                priority="high",
                requires_reply=True,
                confidence=0.91,
                summary="Resumo",
                reason="Motivo",
                risk_flags=[],
            )
        )


@pytest.mark.asyncio
async def test_provider_uses_structured_schema_and_untrusted_input() -> None:
    responses = FakeResponses()
    client = SimpleNamespace(responses=responses)
    provider = OpenAIEmailClassifier(
        api_key="test",
        model="test-model",
        prompt_version="v1",
        timeout_seconds=5,
        retry_attempts=1,
        max_input_characters=5000,
        client=client,  # type: ignore[arg-type]
    )
    item = EmailMessage(
        provider_message_id="msg",
        provider_thread_id="thread",
        sender="sender@example.com",
        recipients=("user@example.com",),
        subject="Projeto",
        received_at=datetime.now(UTC),
        snippet="Preciso de retorno.",
        body_hash="a" * 64,
    )

    result = await provider.classify_email(item)

    assert result.category is EmailCategory.WORK
    assert responses.kwargs["text_format"] is AIEmailClassificationOutput
    assert "UNTRUSTED EMAIL CONTENT" in str(responses.kwargs["input"])
