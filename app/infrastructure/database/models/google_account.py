"""Modelo SQLAlchemy da conta Google autorizada."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base

if TYPE_CHECKING:
    from app.infrastructure.database.models.email_message import EmailMessageModel


class GoogleAccountModel(Base):
    """Credenciais OAuth criptografadas de uma conta Gmail."""

    __tablename__ = "google_accounts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email_address: Mapped[str] = mapped_column(String(320), unique=True)
    encrypted_access_token: Mapped[str] = mapped_column(Text)
    encrypted_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    scopes: Mapped[list[str]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    emails: Mapped[list[EmailMessageModel]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
    )
