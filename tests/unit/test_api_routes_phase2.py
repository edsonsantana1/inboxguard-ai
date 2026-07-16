"""Testes unitários das rotas da Fase 2 sem acessar Google ou PostgreSQL."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.responses import RedirectResponse

from app.application.use_cases.list_emails import EmailPage
from app.core.config import Settings
from app.core.exceptions import ConfigurationError, OAuthDeniedError, OAuthExchangeError
from app.domain.entities.email_message import EmailMessage
from app.domain.entities.google_account import GoogleAccount
from app.domain.entities.sync_result import SyncResult
from app.presentation.api.routes import auth as auth_routes
from app.presentation.api.routes import emails as email_routes


def phase2_settings(*, with_key: bool = True) -> Settings:
    return Settings(
        environment="test",
        database_startup_check=False,
        google_client_id="client",
        google_client_secret="secret",
        token_encryption_key=(
            "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=" if with_key else None
        ),
    )


def persisted_email() -> EmailMessage:
    now = datetime.now(UTC)
    return EmailMessage(
        id=uuid4(),
        account_id=uuid4(),
        provider_message_id="msg-1",
        provider_thread_id="thread-1",
        sender="sender@example.com",
        recipients=("edson@example.com",),
        subject="Subject",
        received_at=now,
        snippet="Snippet",
        body_hash="a" * 64,
        created_at=now,
    )


@pytest.mark.asyncio
async def test_start_google_oauth_returns_redirect(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeStart:
        def __init__(self, *args: object, **kwargs: object) -> None:
            del args, kwargs

        async def execute(self) -> str:
            return "https://accounts.google.test/authorize"

    monkeypatch.setattr(auth_routes, "StartGoogleOAuth", FakeStart)
    monkeypatch.setattr(auth_routes, "SQLAlchemyOAuthStateRepository", lambda session: session)
    monkeypatch.setattr(auth_routes, "GoogleOAuthClient", lambda settings: settings)

    response = await auth_routes.start_google_oauth(
        session=object(),  # type: ignore[arg-type]
        settings=phase2_settings(),
    )

    assert isinstance(response, RedirectResponse)
    assert response.status_code == 307
    assert response.headers["location"] == "https://accounts.google.test/authorize"


@pytest.mark.asyncio
async def test_complete_oauth_rejects_denied_and_incomplete_callbacks() -> None:
    with pytest.raises(OAuthDeniedError):
        await auth_routes.complete_google_oauth(
            code=None,
            state=None,
            error="access_denied",
            session=object(),  # type: ignore[arg-type]
            settings=phase2_settings(),
        )

    with pytest.raises(OAuthExchangeError):
        await auth_routes.complete_google_oauth(
            code=None,
            state="state",
            error=None,
            session=object(),  # type: ignore[arg-type]
            settings=phase2_settings(),
        )


@pytest.mark.asyncio
async def test_complete_oauth_requires_encryption_key() -> None:
    with pytest.raises(ConfigurationError):
        await auth_routes.complete_google_oauth(
            code="code",
            state="state",
            error=None,
            session=object(),  # type: ignore[arg-type]
            settings=phase2_settings(with_key=False),
        )


@pytest.mark.asyncio
async def test_complete_oauth_returns_connected_account(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime.now(UTC)
    account = GoogleAccount(
        id=uuid4(),
        email_address="edson@example.com",
        encrypted_access_token="encrypted-access",
        encrypted_refresh_token="encrypted-refresh",
        token_expires_at=now,
        scopes=("https://www.googleapis.com/auth/gmail.readonly",),
        created_at=now,
        updated_at=now,
    )

    class FakeComplete:
        def __init__(self, *args: object) -> None:
            del args

        async def execute(self, *, state: str, code: str) -> GoogleAccount:
            assert state == "state"
            assert code == "code"
            return account

    monkeypatch.setattr(auth_routes, "CompleteGoogleOAuth", FakeComplete)
    monkeypatch.setattr(auth_routes, "SQLAlchemyOAuthStateRepository", lambda session: session)
    monkeypatch.setattr(auth_routes, "SQLAlchemyGoogleAccountRepository", lambda session: session)
    monkeypatch.setattr(auth_routes, "GoogleOAuthClient", lambda settings: settings)
    monkeypatch.setattr(auth_routes, "FernetTokenCipher", lambda key: key)

    response = await auth_routes.complete_google_oauth(
        code="code",
        state="state",
        error=None,
        session=object(),  # type: ignore[arg-type]
        settings=phase2_settings(),
    )

    assert response.status == "connected"
    assert response.email_address == "edson@example.com"


@pytest.mark.asyncio
async def test_sync_route_requires_encryption_key() -> None:
    with pytest.raises(ConfigurationError):
        await email_routes.sync_emails(
            max_messages=None,
            session=object(),  # type: ignore[arg-type]
            settings=phase2_settings(with_key=False),
        )


@pytest.mark.asyncio
async def test_sync_route_returns_use_case_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeSync:
        def __init__(self, *args: object) -> None:
            del args

        async def execute(self, *, limit: int) -> SyncResult:
            assert limit == 7
            return SyncResult(found=3, stored=2, duplicates=1, failed=0)

    monkeypatch.setattr(email_routes, "SQLAlchemyGoogleAccountRepository", lambda session: session)
    monkeypatch.setattr(email_routes, "SQLAlchemyEmailRepository", lambda session: session)
    monkeypatch.setattr(email_routes, "FernetTokenCipher", lambda key: key)
    monkeypatch.setattr(email_routes, "GmailClient", lambda *args: object())
    monkeypatch.setattr(email_routes, "SyncUnreadEmails", FakeSync)

    response = await email_routes.sync_emails(
        max_messages=7,
        session=object(),  # type: ignore[arg-type]
        settings=phase2_settings(),
    )

    assert response.found == 3
    assert response.stored == 2
    assert response.duplicates == 1


@pytest.mark.asyncio
async def test_list_and_get_routes_serialize_entities(monkeypatch: pytest.MonkeyPatch) -> None:
    email = persisted_email()

    class FakeList:
        def __init__(self, repository: object) -> None:
            del repository

        async def execute(self, *, limit: int, offset: int) -> EmailPage:
            return EmailPage(items=(email,), total=1, limit=limit, offset=offset)

    class FakeGet:
        def __init__(self, repository: object) -> None:
            del repository

        async def execute(self, email_id: object) -> EmailMessage:
            assert email_id == email.id
            return email

    monkeypatch.setattr(email_routes, "SQLAlchemyEmailRepository", lambda session: session)
    monkeypatch.setattr(email_routes, "ListEmails", FakeList)
    monkeypatch.setattr(email_routes, "GetEmail", FakeGet)

    page = await email_routes.list_emails(
        limit=10,
        offset=0,
        session=object(),  # type: ignore[arg-type]
    )
    item = await email_routes.get_email(
        email_id=email.id,  # type: ignore[arg-type]
        session=object(),  # type: ignore[arg-type]
    )

    assert page.total == 1
    assert page.items[0].id == email.id
    assert item.id == email.id
