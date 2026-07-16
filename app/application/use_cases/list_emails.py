"""Caso de uso para listar mensagens persistidas."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities.email_message import EmailMessage
from app.domain.ports.repositories import EmailRepository


@dataclass(frozen=True, slots=True)
class EmailPage:
    """Página simples com total, limite e deslocamento."""

    items: tuple[EmailMessage, ...]
    total: int
    limit: int
    offset: int


class ListEmails:
    """Consulta mensagens sem expor SQLAlchemy à camada HTTP."""

    def __init__(self, repository: EmailRepository) -> None:
        self._repository = repository

    async def execute(self, *, limit: int, offset: int) -> EmailPage:
        """Retorna uma página ordenada pela data de recebimento."""

        items = await self._repository.list(limit=limit, offset=offset)
        total = await self._repository.count()
        return EmailPage(items=tuple(items), total=total, limit=limit, offset=offset)
