"""Repository SQLAlchemy para classificações de e-mail."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.email_classification import EmailClassification
from app.domain.enums.classification_source import ClassificationSource
from app.domain.enums.email_category import EmailCategory
from app.domain.enums.email_priority import EmailPriority
from app.infrastructure.database.models.email_classification import EmailClassificationModel


def _to_entity(model: EmailClassificationModel) -> EmailClassification:
    return EmailClassification(
        id=model.id,
        email_id=model.email_id,
        category=EmailCategory(model.category),
        priority=EmailPriority(model.priority),
        requires_reply=model.requires_reply,
        confidence=model.confidence,
        summary=model.summary,
        reason=model.reason,
        risk_flags=tuple(model.risk_flags),
        source=ClassificationSource(model.source),
        model_name=model.model_name,
        prompt_version=model.prompt_version,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SQLAlchemyEmailClassificationRepository:
    """Persiste a classificação atual com upsert atômico."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email_id(self, email_id: UUID) -> EmailClassification | None:
        statement = select(EmailClassificationModel).where(
            EmailClassificationModel.email_id == email_id
        )
        model = await self._session.scalar(statement)
        return _to_entity(model) if model is not None else None

    async def upsert(self, classification: EmailClassification) -> EmailClassification:
        values = {
            "email_id": classification.email_id,
            "category": classification.category.value,
            "priority": classification.priority.value,
            "requires_reply": classification.requires_reply,
            "confidence": classification.confidence,
            "summary": classification.summary,
            "reason": classification.reason,
            "risk_flags": list(classification.risk_flags),
            "source": classification.source.value,
            "model_name": classification.model_name,
            "prompt_version": classification.prompt_version,
        }
        statement = (
            insert(EmailClassificationModel)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[EmailClassificationModel.email_id],
                set_={**values, "updated_at": func.now()},
            )
            .returning(EmailClassificationModel)
        )
        model = await self._session.scalar(statement)
        if model is None:  # pragma: no cover
            raise RuntimeError("Falha inesperada ao persistir classificação.")
        return _to_entity(model)
