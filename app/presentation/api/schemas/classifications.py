"""Schemas HTTP para classificação explicável."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.entities.email_classification import EmailClassification
from app.domain.enums.classification_source import ClassificationSource
from app.domain.enums.email_category import EmailCategory
from app.domain.enums.email_priority import EmailPriority


class EmailClassificationResponse(BaseModel):
    """Representação pública da classificação persistida."""

    id: UUID
    email_id: UUID
    category: EmailCategory
    priority: EmailPriority
    requires_reply: bool
    confidence: float = Field(ge=0, le=1)
    summary: str
    reason: str
    risk_flags: list[str]
    source: ClassificationSource
    model_name: str
    prompt_version: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, item: EmailClassification) -> EmailClassificationResponse:
        if item.id is None or item.created_at is None or item.updated_at is None:
            raise ValueError("Somente classificações persistidas podem ser serializadas.")
        return cls(
            id=item.id,
            email_id=item.email_id,
            category=item.category,
            priority=item.priority,
            requires_reply=item.requires_reply,
            confidence=item.confidence,
            summary=item.summary,
            reason=item.reason,
            risk_flags=list(item.risk_flags),
            source=item.source,
            model_name=item.model_name,
            prompt_version=item.prompt_version,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
