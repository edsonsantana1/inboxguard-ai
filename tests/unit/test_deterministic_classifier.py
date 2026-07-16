"""Testes das regras determinísticas da Fase 3."""

from datetime import UTC, datetime

from app.domain.entities.email_message import EmailMessage
from app.domain.enums.email_category import EmailCategory
from app.domain.enums.email_priority import EmailPriority
from app.domain.services.deterministic_classifier import DeterministicEmailClassifier


def email(subject: str, snippet: str, *, sender: str = "sender@example.com") -> EmailMessage:
    return EmailMessage(
        provider_message_id="provider-1",
        provider_thread_id="thread-1",
        sender=sender,
        recipients=("user@example.com",),
        subject=subject,
        received_at=datetime.now(UTC),
        snippet=snippet,
        body_hash="a" * 64,
    )


def test_billing_and_critical_priority_are_detected() -> None:
    result = DeterministicEmailClassifier().classify(
        email("Fatura vencida", "Boleto com vencimento hoje. Ação necessária.")
    )

    assert result.category is EmailCategory.BILLING
    assert result.priority is EmailPriority.CRITICAL
    assert "payment_request" in result.risk_flags
    assert result.confidence >= 0.88


def test_newsletter_is_low_priority_and_does_not_require_reply() -> None:
    result = DeterministicEmailClassifier().classify(
        email(
            "Newsletter semanal",
            "Confira as novidades e use o link para cancelar inscrição.",
            sender="news@company.example",
        )
    )

    assert result.category is EmailCategory.NEWSLETTER
    assert result.priority is EmailPriority.LOW
    assert result.requires_reply is False


def test_unknown_message_has_low_confidence_and_can_require_reply() -> None:
    result = DeterministicEmailClassifier().classify(
        email("Olá", "Pode confirmar quando você estará disponível?")
    )

    assert result.category is EmailCategory.UNKNOWN
    assert result.confidence < 0.88
    assert result.requires_reply is True
