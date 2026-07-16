"""Adapter Gmail para leitura de mensagens não lidas."""

from __future__ import annotations

from asyncio import to_thread
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, TypeVar, cast

from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, wait_exponential

from app.core.config import Settings
from app.core.exceptions import ExternalServiceError, GmailAccountNotConnectedError
from app.domain.entities.email_message import EmailMessage
from app.domain.entities.google_account import GoogleAccount
from app.domain.ports.repositories import GoogleAccountRepository
from app.domain.ports.token_cipher import TokenCipher
from app.infrastructure.gmail.message_parser import parse_gmail_message

T = TypeVar("T")
_RECOVERABLE_HTTP_STATUS = {429, 500, 502, 503, 504}


def _to_google_expiry(value: datetime | None) -> datetime | None:
    """Converte expiração para UTC sem tzinfo, formato esperado pelo google-auth."""

    if value is None or value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def _to_storage_expiry(value: datetime | None) -> datetime | None:
    """Converte expiração para UTC com tzinfo antes da persistência."""

    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _is_recoverable(exc: BaseException) -> bool:
    """Limita retentativas a erros transitórios e rate limit."""

    if isinstance(exc, HttpError):
        return int(getattr(exc.resp, "status", 0)) in _RECOVERABLE_HTTP_STATUS
    return isinstance(exc, (ConnectionError, TimeoutError, OSError))


class GmailClient:
    """Lê Gmail com refresh automático, timeout da biblioteca e retries limitados."""

    def __init__(
        self,
        account_repository: GoogleAccountRepository,
        token_cipher: TokenCipher,
        settings: Settings,
    ) -> None:
        self._account_repository = account_repository
        self._token_cipher = token_cipher
        self._settings = settings
        self._service: Resource | None = None
        self._account: GoogleAccount | None = None

    async def _retry(self, operation: Callable[[], T]) -> T:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(self._settings.gmail_retry_attempts),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
            retry=retry_if_exception(_is_recoverable),
            reraise=True,
        ):
            with attempt:
                return await to_thread(operation)
        raise RuntimeError("Fluxo de retry terminou sem resultado.")  # pragma: no cover

    async def _credentials(self) -> Credentials:
        account = await self._account_repository.get_latest()
        if account is None:
            raise GmailAccountNotConnectedError
        self._account = account

        credentials = Credentials(  # type: ignore[no-untyped-call]
            token=self._token_cipher.decrypt(account.encrypted_access_token),
            refresh_token=(
                self._token_cipher.decrypt(account.encrypted_refresh_token)
                if account.encrypted_refresh_token
                else None
            ),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self._settings.google_client_id,
            client_secret=self._settings.google_client_secret,
            scopes=list(account.scopes),
        )
        credentials.expiry = _to_google_expiry(account.token_expires_at)

        if credentials.expired:
            if not credentials.refresh_token:
                raise GmailAccountNotConnectedError
            try:
                await self._retry(
                    lambda: credentials.refresh(  # type: ignore[no-untyped-call]
                        GoogleAuthRequest()
                    )
                )
            except Exception as exc:
                raise ExternalServiceError("Google OAuth") from exc

            expiry = _to_storage_expiry(credentials.expiry)
            await self._account_repository.update_access_token(
                account.id,
                encrypted_access_token=self._token_cipher.encrypt(str(credentials.token)),
                token_expires_at=expiry,
            )

        return credentials

    async def _gmail_service(self) -> Resource:
        if self._service is None:
            credentials = await self._credentials()
            self._service = await to_thread(
                build,
                "gmail",
                "v1",
                credentials=credentials,
                cache_discovery=False,
            )
        return self._service

    async def list_unread_message_ids(self, limit: int) -> list[str]:
        """Lista no máximo `limit` IDs com o label UNREAD."""

        service = await self._gmail_service()
        message_ids: list[str] = []
        page_token: str | None = None

        try:
            while len(message_ids) < limit:
                remaining = limit - len(message_ids)

                def execute_page(
                    current_remaining: int = remaining,
                    current_page_token: str | None = page_token,
                ) -> dict[str, Any]:
                    request = (
                        service.users()
                        .messages()
                        .list(
                            userId="me",
                            labelIds=["UNREAD"],
                            includeSpamTrash=False,
                            maxResults=min(current_remaining, 500),
                            pageToken=current_page_token,
                        )
                    )
                    return cast(dict[str, Any], request.execute())

                response = await self._retry(execute_page)
                message_ids.extend(
                    str(item["id"]) for item in response.get("messages", []) if item.get("id")
                )
                page_token = response.get("nextPageToken")
                if not page_token:
                    break
        except Exception as exc:
            raise ExternalServiceError("Gmail") from exc

        return message_ids[:limit]

    async def get_message(self, message_id: str) -> EmailMessage:
        """Obtém payload completo e o converte em entidade normalizada."""

        service = await self._gmail_service()
        try:
            response = await self._retry(
                lambda: (
                    service.users()
                    .messages()
                    .get(userId="me", id=message_id, format="full")
                    .execute()
                )
            )
        except Exception as exc:
            raise ExternalServiceError("Gmail") from exc

        return parse_gmail_message(
            response,
            store_body_text=self._settings.gmail_store_body_text,
        )
