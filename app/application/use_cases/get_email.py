"""Caso de uso para consultar uma mensagem específica."""

from __future__ import annotations

from uuid import UUID

from app.core.exceptions import ResourceNotFoundError
from app.domain.entities.email_message import EmailMessage
from app.domain.ports.repositories import EmailRepository


class GetEmail:
    """Obtém uma mensagem pelo ID interno."""

    def __init__(self, repository: EmailRepository) -> None:
        self._repository = repository

    async def execute(self, email_id: UUID) -> EmailMessage:
        """Retorna a mensagem ou uma falha controlada."""

        email = await self._repository.get_by_id(email_id)
        if email is None:
            raise ResourceNotFoundError("E-mail")
        return email
