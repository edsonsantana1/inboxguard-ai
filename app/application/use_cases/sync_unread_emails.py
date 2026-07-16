"""Caso de uso de sincronização idempotente de mensagens não lidas."""

from __future__ import annotations

import structlog

from app.core.exceptions import GmailAccountNotConnectedError
from app.domain.entities.sync_result import SyncResult
from app.domain.ports.email_provider import EmailProvider
from app.domain.ports.repositories import EmailRepository, GoogleAccountRepository

logger = structlog.get_logger(__name__)


class SyncUnreadEmails:
    """Orquestra Gmail e persistência sem depender de bibliotecas externas."""

    def __init__(
        self,
        account_repository: GoogleAccountRepository,
        email_repository: EmailRepository,
        email_provider: EmailProvider,
    ) -> None:
        self._account_repository = account_repository
        self._email_repository = email_repository
        self._email_provider = email_provider

    async def execute(self, *, limit: int) -> SyncResult:
        """Busca, normaliza e persiste e-mails, tolerando falhas por mensagem."""

        account = await self._account_repository.get_latest()
        if account is None:
            raise GmailAccountNotConnectedError

        message_ids = await self._email_provider.list_unread_message_ids(limit)
        stored = 0
        duplicates = 0
        failed_ids: list[str] = []

        for message_id in message_ids:
            try:
                email = await self._email_provider.get_message(message_id)
            except Exception as exc:  # Uma mensagem malformada não invalida todo o lote.
                logger.warning(
                    "gmail_message_sync_failed",
                    provider_message_id=message_id,
                    error_type=type(exc).__name__,
                )
                failed_ids.append(message_id)
                continue

            # Erros de persistência não são ocultados: uma transação inválida deve falhar.
            inserted = await self._email_repository.add_if_absent(account.id, email)
            if inserted:
                stored += 1
            else:
                duplicates += 1

        return SyncResult(
            found=len(message_ids),
            stored=stored,
            duplicates=duplicates,
            failed=len(failed_ids),
            failed_message_ids=tuple(failed_ids),
        )
