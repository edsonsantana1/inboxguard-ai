"""Porta do provedor de mensagens."""

from typing import Protocol

from app.domain.entities.email_message import EmailMessage


class EmailProvider(Protocol):
    """Expõe apenas operações necessárias para sincronizar mensagens."""

    async def list_unread_message_ids(self, limit: int) -> list[str]:
        """Lista IDs de mensagens não lidas sem carregar o conteúdo completo."""
        raise NotImplementedError

    async def get_message(self, message_id: str) -> EmailMessage:
        """Obtém e normaliza uma mensagem específica."""
        raise NotImplementedError
