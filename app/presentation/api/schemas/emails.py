"""Schemas HTTP da sincronização e consulta de e-mails."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.entities.email_message import EmailMessage
from app.domain.enums.email_status import EmailStatus


class EmailResponse(BaseModel):
    """Metadados seguros de uma mensagem persistida."""

    id: UUID
    provider_message_id: str
    provider_thread_id: str
    sender: str
    recipients: list[str]
    subject: str
    received_at: datetime
    snippet: str
    body_text: str | None
    body_hash: str
    status: EmailStatus
    processed_at: datetime | None
    created_at: datetime

    @classmethod
    def from_entity(cls, email: EmailMessage) -> EmailResponse:
        """Converte uma entidade já persistida em contrato HTTP."""

        if email.id is None or email.created_at is None:
            raise ValueError("Somente mensagens persistidas podem ser serializadas.")
        return cls(
            id=email.id,
            provider_message_id=email.provider_message_id,
            provider_thread_id=email.provider_thread_id,
            sender=email.sender,
            recipients=list(email.recipients),
            subject=email.subject,
            received_at=email.received_at,
            snippet=email.snippet,
            body_text=email.body_text,
            body_hash=email.body_hash,
            status=email.status,
            processed_at=email.processed_at,
            created_at=email.created_at,
        )


class EmailListResponse(BaseModel):
    """Página de mensagens persistidas."""

    items: list[EmailResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)


class EmailSyncResponse(BaseModel):
    """Contadores da sincronização idempotente."""

    found: int = Field(ge=0)
    stored: int = Field(ge=0)
    duplicates: int = Field(ge=0)
    failed: int = Field(ge=0)
    failed_message_ids: list[str] = Field(default_factory=list)
