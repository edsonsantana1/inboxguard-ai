"""Testes do caso de uso de classificação com regras, IA e fallback."""

from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.application.use_cases.classify_email import ClassifyEmail
from app.domain.entities.classification_candidate import ClassificationCandidate
from app.domain.entities.email_classification import EmailClassification
from app.domain.entities.email_message import EmailMessage
from app.domain.enums.classification_source import ClassificationSource
from app.domain.enums.email_category import EmailCategory
from app.domain.enums.email_priority import EmailPriority
from app.domain.services.deterministic_classifier import DeterministicEmailClassifier


class EmailRepo:
    def __init__(self, item: EmailMessage | None) -> None:
        self.item = item

    async def get_by_id(self, email_id: UUID) -> EmailMessage | None:
        del email_id
        return self.item


class ClassificationRepo:
    def __init__(self, existing: EmailClassification | None = None) -> None:
        self.existing = existing
        self.saved: EmailClassification | None = None

    async def get_by_email_id(self, email_id: UUID) -> EmailClassification | None:
        del email_id
        return self.existing

    async def upsert(self, item: EmailClassification) -> EmailClassification:
        now = datetime.now(UTC)
        self.saved = replace(
            item,
            id=item.id or uuid4(),
            created_at=item.created_at or now,
            updated_at=now,
        )
        return self.saved


class FakeAI:
    model_name = "fake-model"
    prompt_version = "test-v1"

    def __init__(self, *, error: Exception | None = None) -> None:
        self.calls = 0
        self.error = error

    async def classify_email(self, email: EmailMessage) -> ClassificationCandidate:
        del email
        self.calls += 1
        if self.error:
            raise self.error
        return ClassificationCandidate(
            category=EmailCategory.WORK,
            priority=EmailPriority.HIGH,
            requires_reply=True,
            confidence=0.94,
            summary="Solicitação de trabalho.",
            reason="Solicitação direta identificada pela IA.",
            risk_flags=(),
        )


def message(subject: str, snippet: str) -> EmailMessage:
    return EmailMessage(
        id=uuid4(),
        account_id=uuid4(),
        provider_message_id="msg",
        provider_thread_id="thread",
        sender="sender@example.com",
        recipients=("user@example.com",),
        subject=subject,
        received_at=datetime.now(UTC),
        snippet=snippet,
        body_hash="a" * 64,
        created_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_strong_deterministic_result_skips_ai() -> None:
    item = message("Fatura vencida", "Boleto com vencimento hoje e ação necessária.")
    ai = FakeAI()
    repo = ClassificationRepo()
    result = await ClassifyEmail(
        EmailRepo(item),
        repo,
        DeterministicEmailClassifier(),
        ai,
        deterministic_threshold=0.88,
    ).execute(item.id)  # type: ignore[arg-type]

    assert result.source is ClassificationSource.DETERMINISTIC
    assert ai.calls == 0


@pytest.mark.asyncio
async def test_uncertain_result_uses_ai() -> None:
    item = message("Olá", "Podemos conversar sobre isso?")
    ai = FakeAI()
    result = await ClassifyEmail(
        EmailRepo(item),
        ClassificationRepo(),
        DeterministicEmailClassifier(),
        ai,
        deterministic_threshold=0.88,
    ).execute(item.id)  # type: ignore[arg-type]

    assert result.source is ClassificationSource.AI
    assert result.category is EmailCategory.WORK
    assert ai.calls == 1


@pytest.mark.asyncio
async def test_ai_failure_uses_deterministic_fallback() -> None:
    item = message("Olá", "Mensagem sem indicadores suficientes.")
    ai = FakeAI(error=RuntimeError("provider unavailable"))
    result = await ClassifyEmail(
        EmailRepo(item),
        ClassificationRepo(),
        DeterministicEmailClassifier(),
        ai,
        deterministic_threshold=0.88,
    ).execute(item.id)  # type: ignore[arg-type]

    assert result.source is ClassificationSource.FALLBACK
    assert result.category is EmailCategory.UNKNOWN


@pytest.mark.asyncio
async def test_existing_result_is_reused_without_ai_cost() -> None:
    item = message("Olá", "Mensagem.")
    now = datetime.now(UTC)
    existing = EmailClassification(
        id=uuid4(),
        email_id=item.id,  # type: ignore[arg-type]
        category=EmailCategory.PERSONAL,
        priority=EmailPriority.LOW,
        requires_reply=False,
        confidence=0.8,
        summary="Existente",
        reason="Existente",
        risk_flags=(),
        source=ClassificationSource.DETERMINISTIC,
        model_name="rules",
        prompt_version="v1",
        created_at=now,
        updated_at=now,
    )
    ai = FakeAI()
    result = await ClassifyEmail(
        EmailRepo(item),
        ClassificationRepo(existing),
        DeterministicEmailClassifier(),
        ai,
        deterministic_threshold=0.88,
    ).execute(item.id)  # type: ignore[arg-type]

    assert result is existing
    assert ai.calls == 0
