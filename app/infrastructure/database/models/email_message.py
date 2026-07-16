"""Modelo SQLAlchemy de mensagem de e-mail normalizada."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums.email_status import EmailStatus
from app.infrastructure.database.base import Base

if TYPE_CHECKING:
    from app.infrastructure.database.models.google_account import GoogleAccountModel


class EmailMessageModel(Base):
    """Metadados persistidos com corpo opcional e idempotência por conta."""

    __tablename__ = "email_messages"
    __table_args__ = (
        UniqueConstraint(
            "google_account_id",
            "provider_message_id",
            name="uq_email_messages_account_provider_message",
        ),
        CheckConstraint(
            "status IN ('pending', 'processed', 'ignored')",
            name="email_message_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    google_account_id: Mapped[UUID] = mapped_column(
        ForeignKey("google_accounts.id", ondelete="CASCADE"), index=True
    )
    provider_message_id: Mapped[str] = mapped_column(String(255))
    provider_thread_id: Mapped[str] = mapped_column(String(255), index=True)
    sender: Mapped[str] = mapped_column(String(998))
    recipients: Mapped[list[str]] = mapped_column(JSONB, default=list)
    subject: Mapped[str] = mapped_column(String(998), default="(sem assunto)")
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    snippet: Mapped[str] = mapped_column(Text, default="")
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_hash: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default=EmailStatus.PENDING.value)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    account: Mapped[GoogleAccountModel] = relationship(back_populates="emails")
