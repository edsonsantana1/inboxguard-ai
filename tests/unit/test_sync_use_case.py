"""Testes da sincronização idempotente de e-mails."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.application.use_cases.sync_unread_emails import SyncUnreadEmails
from app.core.exceptions import GmailAccountNotConnectedError
from app.domain.entities.email_message import EmailMessage
from app.domain.entities.google_account import GoogleAccount


class FakeAccountRepository:
    def __init__(self, account: GoogleAccount | None) -> None:
        self.account = account

    async def get_latest(self) -> GoogleAccount | None:
        return self.account

    async def get_by_email(self, email_address: str) -> GoogleAccount | None:
        del email_address
        return self.account

    async def upsert(self, **kwargs: object) -> GoogleAccount:
        del kwargs
        assert self.account is not None
        return self.account

    async def update_access_token(self, account_id: UUID, **kwargs: object) -> None:
        del account_id, kwargs


class FakeEmailProvider:
    def __init__(self) -> None:
        self.requested_limit: int | None = None

    async def list_unread_message_ids(self, limit: int) -> list[str]:
        self.requested_limit = limit
        return ["new", "duplicate", "broken"]

    async def get_message(self, message_id: str) -> EmailMessage:
        if message_id == "broken":
            raise ValueError("malformed MIME")
        return build_email(message_id)


class FakeEmailRepository:
    def __init__(self, *, persistence_error: bool = False) -> None:
        self.persistence_error = persistence_error
        self.saved: list[str] = []

    async def add_if_absent(self, account_id: UUID, email: EmailMessage) -> bool:
        del account_id
        if self.persistence_error:
            raise RuntimeError("database error")
        self.saved.append(email.provider_message_id)
        return email.provider_message_id != "duplicate"

    async def list(self, *, limit: int, offset: int) -> list[EmailMessage]:
        del limit, offset
        return []

    async def count(self) -> int:
        return 0

    async def get_by_id(self, email_id: UUID) -> EmailMessage | None:
        del email_id
        return None


def build_account() -> GoogleAccount:
    now = datetime.now(UTC)
    return GoogleAccount(
        id=uuid4(),
        email_address="edson@example.com",
        encrypted_access_token="access",
        encrypted_refresh_token="refresh",
        token_expires_at=now,
        scopes=("https://www.googleapis.com/auth/gmail.readonly",),
        created_at=now,
        updated_at=now,
    )


def build_email(message_id: str) -> EmailMessage:
    return EmailMessage(
        provider_message_id=message_id,
        provider_thread_id=f"thread-{message_id}",
        sender="sender@example.com",
        recipients=("edson@example.com",),
        subject="Subject",
        received_at=datetime.now(UTC),
        snippet="Snippet",
        body_hash="0" * 64,
    )


@pytest.mark.asyncio
async def test_sync_counts_new_duplicate_and_failed_messages() -> None:
    provider = FakeEmailProvider()
    repository = FakeEmailRepository()
    use_case = SyncUnreadEmails(
        FakeAccountRepository(build_account()),
        repository,
        provider,
    )

    result = await use_case.execute(limit=25)

    assert provider.requested_limit == 25
    assert result.found == 3
    assert result.stored == 1
    assert result.duplicates == 1
    assert result.failed == 1
    assert result.failed_message_ids == ("broken",)
    assert repository.saved == ["new", "duplicate"]


@pytest.mark.asyncio
async def test_sync_requires_connected_gmail_account() -> None:
    use_case = SyncUnreadEmails(
        FakeAccountRepository(None),
        FakeEmailRepository(),
        FakeEmailProvider(),
    )

    with pytest.raises(GmailAccountNotConnectedError):
        await use_case.execute(limit=10)


@pytest.mark.asyncio
async def test_sync_does_not_hide_database_failures() -> None:
    use_case = SyncUnreadEmails(
        FakeAccountRepository(build_account()),
        FakeEmailRepository(persistence_error=True),
        FakeEmailProvider(),
    )

    with pytest.raises(RuntimeError, match="database error"):
        await use_case.execute(limit=10)
