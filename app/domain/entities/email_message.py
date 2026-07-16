"""Entidade normalizada de mensagem de e-mail."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.enums.email_status import EmailStatus


@dataclass(frozen=True, slots=True)
class EmailMessage:
    """Representação independente do formato MIME específico do Gmail."""

    provider_message_id: str
    provider_thread_id: str
    sender: str
    recipients: tuple[str, ...]
    subject: str
    received_at: datetime
    snippet: str
    body_hash: str
    body_text: str | None = None
    status: EmailStatus = EmailStatus.PENDING
    id: UUID | None = None
    account_id: UUID | None = None
    processed_at: datetime | None = None
    created_at: datetime | None = None
