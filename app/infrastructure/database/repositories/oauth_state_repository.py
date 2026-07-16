"""Repository SQLAlchemy para state OAuth descartável."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.oauth_state import OAuthStateModel


class SQLAlchemyOAuthStateRepository:
    """Persiste somente o hash do state e o consome atomicamente."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, state_hash: str, expires_at: datetime) -> None:
        """Adiciona um state com expiração curta."""

        self._session.add(OAuthStateModel(state_hash=state_hash, expires_at=expires_at))
        await self._session.flush()

    async def consume(self, state_hash: str, now: datetime) -> bool:
        """Marca um state como usado somente quando ainda for válido."""

        statement = (
            update(OAuthStateModel)
            .where(
                and_(
                    OAuthStateModel.state_hash == state_hash,
                    OAuthStateModel.used_at.is_(None),
                    OAuthStateModel.expires_at > now,
                )
            )
            .values(used_at=now)
            .returning(OAuthStateModel.id)
        )
        consumed_id = await self._session.scalar(statement)
        return consumed_id is not None
