"""Testes dos schemas HTTP de e-mail."""

from datetime import UTC, datetime

import pytest

from app.domain.entities.email_message import EmailMessage
from app.presentation.api.schemas.emails import EmailResponse


def test_email_response_rejects_non_persisted_entity() -> None:
    email = EmailMessage(
        provider_message_id="msg",
        provider_thread_id="thread",
        sender="sender@example.com",
        recipients=(),
        subject="Subject",
        received_at=datetime.now(UTC),
        snippet="Snippet",
        body_hash="0" * 64,
    )

    with pytest.raises(ValueError, match="persistidas"):
        EmailResponse.from_entity(email)
