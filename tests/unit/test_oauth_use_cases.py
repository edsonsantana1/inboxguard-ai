"""Testes dos casos de uso de autorização Google OAuth."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

import pytest

from app.application.use_cases.complete_google_oauth import CompleteGoogleOAuth
from app.application.use_cases.start_google_oauth import StartGoogleOAuth
from app.core.exceptions import InvalidOAuthStateError
from app.domain.entities.google_account import GoogleAccount
from app.domain.entities.oauth_tokens import OAuthTokenSet


class FakeStateRepository:
    """Repository de state controlado pelos testes."""

    def __init__(self, *, consume_result: bool = True) -> None:
        self.consume_result = consume_result
        self.created_hash: str | None = None
        self.expires_at: datetime | None = None
        self.consumed_hash: str | None = None

    async def create(self, state_hash: str, expires_at: datetime) -> None:
        self.created_hash = state_hash
        self.expires_at = expires_at

    async def consume(self, state_hash: str, now: datetime) -> bool:
        del now
        self.consumed_hash = state_hash
        return self.consume_result


class FakeOAuthProvider:
    """Provider OAuth sem chamadas de rede."""

    def __init__(self, token_set: OAuthTokenSet | None = None) -> None:
        self.raw_state: str | None = None
        self.code: str | None = None
        self.token_set = token_set

    def build_authorization_url(self, state: str) -> str:
        self.raw_state = state
        return f"https://accounts.example/authorize?state={state}"

    async def exchange_code(self, code: str) -> OAuthTokenSet:
        self.code = code
        assert self.token_set is not None
        return self.token_set


class FakeCipher:
    """Cipher determinístico que permite inspecionar os valores persistidos."""

    def encrypt(self, plaintext: str) -> str:
        return f"encrypted::{plaintext}"

    def decrypt(self, ciphertext: str) -> str:
        return ciphertext.removeprefix("encrypted::")


class FakeAccountRepository:
    """Repository de conta em memória."""

    def __init__(self, existing: GoogleAccount | None = None) -> None:
        self.existing = existing
        self.upsert_kwargs: dict[str, object] | None = None

    async def get_latest(self) -> GoogleAccount | None:
        return self.existing

    async def get_by_email(self, email_address: str) -> GoogleAccount | None:
        if self.existing and self.existing.email_address == email_address:
            return self.existing
        return None

    async def upsert(self, **kwargs: object) -> GoogleAccount:
        self.upsert_kwargs = kwargs
        now = datetime.now(UTC)
        return GoogleAccount(
            id=self.existing.id if self.existing else uuid4(),
            email_address=str(kwargs["email_address"]),
            encrypted_access_token=str(kwargs["encrypted_access_token"]),
            encrypted_refresh_token=(
                str(kwargs["encrypted_refresh_token"])
                if kwargs["encrypted_refresh_token"] is not None
                else None
            ),
            token_expires_at=kwargs["token_expires_at"],  # type: ignore[arg-type]
            scopes=kwargs["scopes"],  # type: ignore[arg-type]
            created_at=now,
            updated_at=now,
        )

    async def update_access_token(self, *args: object, **kwargs: object) -> None:
        del args, kwargs


def build_token_set(*, refresh_token: str | None = "refresh") -> OAuthTokenSet:
    return OAuthTokenSet(
        email_address="edson@example.com",
        access_token="access",
        refresh_token=refresh_token,
        expires_at=datetime(2026, 7, 15, tzinfo=UTC),
        scopes=("https://www.googleapis.com/auth/gmail.readonly",),
    )


@pytest.mark.asyncio
async def test_start_oauth_stores_only_hash_and_returns_provider_url() -> None:
    states = FakeStateRepository()
    provider = FakeOAuthProvider()
    use_case = StartGoogleOAuth(states, provider, state_ttl_seconds=600)

    url = await use_case.execute()

    assert provider.raw_state is not None
    assert provider.raw_state in url
    assert states.created_hash == sha256(provider.raw_state.encode()).hexdigest()
    assert states.created_hash != provider.raw_state
    assert states.expires_at is not None


@pytest.mark.asyncio
async def test_complete_oauth_encrypts_tokens_before_persistence() -> None:
    states = FakeStateRepository()
    accounts = FakeAccountRepository()
    provider = FakeOAuthProvider(build_token_set())
    use_case = CompleteGoogleOAuth(states, accounts, provider, FakeCipher())

    account = await use_case.execute(state="state-123", code="code-123")

    assert states.consumed_hash == sha256(b"state-123").hexdigest()
    assert provider.code == "code-123"
    assert accounts.upsert_kwargs is not None
    assert accounts.upsert_kwargs["encrypted_access_token"] == "encrypted::access"
    assert accounts.upsert_kwargs["encrypted_refresh_token"] == "encrypted::refresh"
    assert account.email_address == "edson@example.com"


@pytest.mark.asyncio
async def test_complete_oauth_reuses_existing_refresh_token_when_google_omits_it() -> None:
    now = datetime.now(UTC)
    existing = GoogleAccount(
        id=uuid4(),
        email_address="edson@example.com",
        encrypted_access_token="encrypted::old-access",
        encrypted_refresh_token="encrypted::old-refresh",
        token_expires_at=now,
        scopes=("https://www.googleapis.com/auth/gmail.readonly",),
        created_at=now,
        updated_at=now,
    )
    accounts = FakeAccountRepository(existing)
    use_case = CompleteGoogleOAuth(
        FakeStateRepository(),
        accounts,
        FakeOAuthProvider(build_token_set(refresh_token=None)),
        FakeCipher(),
    )

    await use_case.execute(state="valid", code="code")

    assert accounts.upsert_kwargs is not None
    assert accounts.upsert_kwargs["encrypted_refresh_token"] == "encrypted::old-refresh"


@pytest.mark.asyncio
async def test_complete_oauth_rejects_expired_or_reused_state() -> None:
    provider = FakeOAuthProvider(build_token_set())
    use_case = CompleteGoogleOAuth(
        FakeStateRepository(consume_result=False),
        FakeAccountRepository(),
        provider,
        FakeCipher(),
    )

    with pytest.raises(InvalidOAuthStateError):
        await use_case.execute(state="invalid", code="code")

    assert provider.code is None
