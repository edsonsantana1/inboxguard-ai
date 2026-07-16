"""Entidade de classificação explicável de e-mail."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.enums.classification_source import ClassificationSource
from app.domain.enums.email_category import EmailCategory
from app.domain.enums.email_priority import EmailPriority


@dataclass(frozen=True, slots=True)
class EmailClassification:
    """Resultado validado e independente de qualquer provedor de IA."""

    email_id: UUID
    category: EmailCategory
    priority: EmailPriority
    requires_reply: bool
    confidence: float
    summary: str
    reason: str
    risk_flags: tuple[str, ...]
    source: ClassificationSource
    model_name: str
    prompt_version: str
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
