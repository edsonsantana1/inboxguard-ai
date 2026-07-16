"""Repository SQLAlchemy para mensagens normalizadas."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.email_message import EmailMessage
from app.domain.enums.email_status import EmailStatus
from app.infrastructure.database.models.email_message import EmailMessageModel


def _to_entity(model: EmailMessageModel) -> EmailMessage:
    """Converte um registro SQLAlchemy em entidade imutável."""

    return EmailMessage(
        id=model.id,
        account_id=model.google_account_id,
        provider_message_id=model.provider_message_id,
        provider_thread_id=model.provider_thread_id,
        sender=model.sender,
        recipients=tuple(model.recipients),
        subject=model.subject,
        received_at=model.received_at,
        snippet=model.snippet,
        body_text=model.body_text,
        body_hash=model.body_hash,
        status=EmailStatus(model.status),
        processed_at=model.processed_at,
        created_at=model.created_at,
    )


class SQLAlchemyEmailRepository:
    """Garante idempotência por restrição UNIQUE e ON CONFLICT."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_if_absent(self, account_id: UUID, email: EmailMessage) -> bool:
        """Insere sem corrida entre verificação e gravação."""

        statement = (
            insert(EmailMessageModel)
            .values(
                google_account_id=account_id,
                provider_message_id=email.provider_message_id,
                provider_thread_id=email.provider_thread_id,
                sender=email.sender,
                recipients=list(email.recipients),
                subject=email.subject,
                received_at=email.received_at,
                snippet=email.snippet,
                body_text=email.body_text,
                body_hash=email.body_hash,
                status=email.status.value,
                processed_at=email.processed_at,
            )
            .on_conflict_do_nothing(constraint="uq_email_messages_account_provider_message")
            .returning(EmailMessageModel.id)
        )
        inserted_id = await self._session.scalar(statement)
        return inserted_id is not None

    async def list(self, *, limit: int, offset: int) -> list[EmailMessage]:
        """Lista mensagens com paginação estável."""

        statement = (
            select(EmailMessageModel)
            .order_by(EmailMessageModel.received_at.desc(), EmailMessageModel.id.desc())
            .limit(limit)
            .offset(offset)
        )
        models = (await self._session.scalars(statement)).all()
        return [_to_entity(model) for model in models]

    async def count(self) -> int:
        """Retorna o total de mensagens armazenadas."""

        statement = select(func.count()).select_from(EmailMessageModel)
        return int(await self._session.scalar(statement) or 0)

    async def get_by_id(self, email_id: UUID) -> EmailMessage | None:
        """Busca um registro pelo UUID interno."""

        model = await self._session.get(EmailMessageModel, email_id)
        return _to_entity(model) if model is not None else None
