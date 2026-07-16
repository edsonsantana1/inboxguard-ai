"""Testes dos casos de uso de consulta de mensagens."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.application.use_cases.get_email import GetEmail
from app.application.use_cases.list_emails import ListEmails
from app.core.exceptions import ResourceNotFoundError
from app.domain.entities.email_message import EmailMessage


class FakeEmailRepository:
    def __init__(self, items: list[EmailMessage]) -> None:
        self.items = items

    async def add_if_absent(self, account_id: UUID, email: EmailMessage) -> bool:
        del account_id, email
        return True

    async def list(self, *, limit: int, offset: int) -> list[EmailMessage]:
        return self.items[offset : offset + limit]

    async def count(self) -> int:
        return len(self.items)

    async def get_by_id(self, email_id: UUID) -> EmailMessage | None:
        return next((item for item in self.items if item.id == email_id), None)


def build_email() -> EmailMessage:
    now = datetime.now(UTC)
    return EmailMessage(
        id=uuid4(),
        account_id=uuid4(),
        provider_message_id="msg",
        provider_thread_id="thread",
        sender="sender@example.com",
        recipients=("edson@example.com",),
        subject="Subject",
        received_at=now,
        snippet="Snippet",
        body_hash="1" * 64,
        created_at=now,
    )


@pytest.mark.asyncio
async def test_list_emails_returns_page_metadata() -> None:
    email = build_email()
    page = await ListEmails(FakeEmailRepository([email])).execute(limit=10, offset=0)

    assert page.items == (email,)
    assert page.total == 1
    assert page.limit == 10
    assert page.offset == 0


@pytest.mark.asyncio
async def test_get_email_returns_item() -> None:
    email = build_email()
    result = await GetEmail(FakeEmailRepository([email])).execute(
        email.id  # type: ignore[arg-type]
    )
    assert result == email


@pytest.mark.asyncio
async def test_get_email_raises_safe_not_found_error() -> None:
    with pytest.raises(ResourceNotFoundError):
        await GetEmail(FakeEmailRepository([])).execute(uuid4())
