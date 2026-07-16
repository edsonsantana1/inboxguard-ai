"""Portas de persistência usadas pelos casos de uso."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.domain.entities.email_classification import EmailClassification
from app.domain.entities.email_message import EmailMessage
from app.domain.entities.google_account import GoogleAccount


class OAuthStateRepository(Protocol):
    """Persiste state OAuth com expiração e consumo único."""

    async def create(self, state_hash: str, expires_at: datetime) -> None:
        """Armazena somente o hash do state."""
        raise NotImplementedError

    async def consume(self, state_hash: str, now: datetime) -> bool:
        """Consome atomicamente um state válido."""
        raise NotImplementedError


class GoogleAccountRepository(Protocol):
    """Persiste credenciais Google criptografadas."""

    async def get_latest(self) -> GoogleAccount | None:
        """Retorna a conta conectada mais recente do MVP de usuário único."""
        raise NotImplementedError

    async def get_by_email(self, email_address: str) -> GoogleAccount | None:
        """Busca uma conta pelo endereço normalizado."""
        raise NotImplementedError

    async def upsert(
        self,
        *,
        email_address: str,
        encrypted_access_token: str,
        encrypted_refresh_token: str | None,
        token_expires_at: datetime | None,
        scopes: tuple[str, ...],
    ) -> GoogleAccount:
        """Cria ou atualiza a única credencial da conta."""
        raise NotImplementedError

    async def update_access_token(
        self,
        account_id: UUID,
        *,
        encrypted_access_token: str,
        token_expires_at: datetime | None,
    ) -> None:
        """Persiste um access token renovado."""
        raise NotImplementedError


class EmailRepository(Protocol):
    """Persiste e consulta mensagens normalizadas."""

    async def add_if_absent(self, account_id: UUID, email: EmailMessage) -> bool:
        """Insere uma mensagem ou retorna falso quando ela já existe."""
        raise NotImplementedError

    async def list(self, *, limit: int, offset: int) -> list[EmailMessage]:
        """Lista mensagens da mais recente para a mais antiga."""
        raise NotImplementedError

    async def count(self) -> int:
        """Retorna o total de mensagens persistidas."""
        raise NotImplementedError

    async def get_by_id(self, email_id: UUID) -> EmailMessage | None:
        """Busca uma mensagem pelo identificador interno."""
        raise NotImplementedError


class EmailClassificationRepository(Protocol):
    """Persiste e consulta a classificação atual de cada e-mail."""

    async def get_by_email_id(self, email_id: UUID) -> EmailClassification | None:
        """Busca a classificação associada ao e-mail."""
        raise NotImplementedError

    async def upsert(self, classification: EmailClassification) -> EmailClassification:
        """Cria ou substitui atomicamente a classificação atual."""
        raise NotImplementedError
