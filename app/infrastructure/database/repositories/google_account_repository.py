"""Repository SQLAlchemy para credenciais Google criptografadas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.google_account import GoogleAccount
from app.infrastructure.database.models.google_account import GoogleAccountModel


def _to_entity(model: GoogleAccountModel) -> GoogleAccount:
    """Converte o modelo persistente em entidade independente de ORM."""

    return GoogleAccount(
        id=model.id,
        email_address=model.email_address,
        encrypted_access_token=model.encrypted_access_token,
        encrypted_refresh_token=model.encrypted_refresh_token,
        token_expires_at=model.token_expires_at,
        scopes=tuple(model.scopes),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SQLAlchemyGoogleAccountRepository:
    """Armazena uma ou mais contas, embora o MVP use apenas a mais recente."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_latest(self) -> GoogleAccount | None:
        """Retorna a conta atual do MVP de usuário único."""

        statement = (
            select(GoogleAccountModel).order_by(GoogleAccountModel.updated_at.desc()).limit(1)
        )
        model = await self._session.scalar(statement)
        return _to_entity(model) if model is not None else None

    async def get_by_email(self, email_address: str) -> GoogleAccount | None:
        """Busca uma conta pelo endereço em minúsculas."""

        statement = select(GoogleAccountModel).where(
            GoogleAccountModel.email_address == email_address.lower()
        )
        model = await self._session.scalar(statement)
        return _to_entity(model) if model is not None else None

    async def upsert(
        self,
        *,
        email_address: str,
        encrypted_access_token: str,
        encrypted_refresh_token: str | None,
        token_expires_at: datetime | None,
        scopes: tuple[str, ...],
    ) -> GoogleAccount:
        """Cria ou atualiza credenciais sem apagar refresh token existente."""

        normalized_email = email_address.lower()
        statement = select(GoogleAccountModel).where(
            GoogleAccountModel.email_address == normalized_email
        )
        model = await self._session.scalar(statement)

        if model is None:
            model = GoogleAccountModel(
                email_address=normalized_email,
                encrypted_access_token=encrypted_access_token,
                encrypted_refresh_token=encrypted_refresh_token,
                token_expires_at=token_expires_at,
                scopes=list(scopes),
            )
            self._session.add(model)
        else:
            model.encrypted_access_token = encrypted_access_token
            if encrypted_refresh_token is not None:
                model.encrypted_refresh_token = encrypted_refresh_token
            model.token_expires_at = token_expires_at
            model.scopes = list(scopes)

        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def update_access_token(
        self,
        account_id: UUID,
        *,
        encrypted_access_token: str,
        token_expires_at: datetime | None,
    ) -> None:
        """Atualiza somente o token curto após refresh automático."""

        statement = (
            update(GoogleAccountModel)
            .where(GoogleAccountModel.id == account_id)
            .values(
                encrypted_access_token=encrypted_access_token,
                token_expires_at=token_expires_at,
            )
        )
        await self._session.execute(statement)
