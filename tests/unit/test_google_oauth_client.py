"""Testes do adapter Google OAuth sem comunicação externa."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.core.config import Settings
from app.core.exceptions import ConfigurationError, OAuthExchangeError
from app.domain.entities.oauth_tokens import OAuthTokenSet
from app.infrastructure.gmail import google_oauth_client as oauth_module
from app.infrastructure.gmail.google_oauth_client import GoogleOAuthClient


def valid_settings() -> Settings:
    """Cria configuração completa e segura para os testes do OAuth."""

    return Settings(
        environment="test",
        google_client_id="client-id",
        google_client_secret="client-secret",
        google_redirect_uri=("http://localhost:8000/auth/google/callback"),
        token_encryption_key="configured-key",
    )


def test_oauth_client_requires_google_credentials_and_cipher_key() -> None:
    """Exige credenciais Google e chave de criptografia."""

    with pytest.raises(
        ConfigurationError,
        match="GOOGLE_CLIENT_ID",
    ):
        GoogleOAuthClient(
            Settings(
                token_encryption_key="key",
            )
        )

    with pytest.raises(
        ConfigurationError,
        match="TOKEN_ENCRYPTION_KEY",
    ):
        GoogleOAuthClient(
            Settings(
                google_client_id="client",
                google_client_secret="secret",
            )
        )


def test_build_authorization_url_uses_web_flow_and_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valida a criação do fluxo OAuth e o estado antifalsificação."""

    captured: dict[str, object] = {}

    class FakeFlow:
        """Substituto do Flow do Google sem chamadas externas."""

        redirect_uri: str | None = None

        @classmethod
        def from_client_config(
            cls,
            config: dict[str, object],
            scopes: list[str],
            **kwargs: object,
        ) -> FakeFlow:
            captured["config"] = config
            captured["scopes"] = scopes
            captured["flow_kwargs"] = kwargs

            return cls()

        def authorization_url(
            self,
            **kwargs: object,
        ) -> tuple[str, str]:
            captured["authorization_kwargs"] = kwargs

            return (
                "https://accounts.google.test/authorize",
                "ignored-state",
            )

    monkeypatch.setattr(
        oauth_module,
        "Flow",
        FakeFlow,
    )

    client = GoogleOAuthClient(valid_settings())

    url = client.build_authorization_url("state-123")

    assert url == "https://accounts.google.test/authorize"

    assert captured["scopes"] == ["https://www.googleapis.com/auth/gmail.readonly"]

    flow_kwargs = captured["flow_kwargs"]

    assert isinstance(flow_kwargs, dict)
    assert flow_kwargs["autogenerate_code_verifier"] is False

    authorization_kwargs = captured["authorization_kwargs"]

    assert isinstance(authorization_kwargs, dict)
    assert authorization_kwargs["state"] == "state-123"
    assert authorization_kwargs["access_type"] == "offline"
    assert authorization_kwargs["prompt"] == "consent"


@pytest.mark.asyncio
async def test_exchange_code_returns_token_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retorna tokens normalizados após uma troca válida."""

    expected = OAuthTokenSet(
        email_address="usuario@example.com",
        access_token="access",
        refresh_token="refresh",
        expires_at=datetime(
            2026,
            7,
            15,
            tzinfo=UTC,
        ),
        scopes=("https://www.googleapis.com/auth/gmail.readonly",),
    )

    client = GoogleOAuthClient(valid_settings())

    monkeypatch.setattr(
        client,
        "_exchange_code_sync",
        lambda code: expected,
    )

    result = await client.exchange_code("code")

    assert result == expected


@pytest.mark.asyncio
async def test_exchange_code_wraps_invalid_provider_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Converte falhas do provedor em erro seguro da aplicação."""

    client = GoogleOAuthClient(valid_settings())

    def fail(code: str) -> OAuthTokenSet:
        del code
        raise ValueError("invalid code")

    monkeypatch.setattr(
        client,
        "_exchange_code_sync",
        fail,
    )

    with pytest.raises(OAuthExchangeError):
        await client.exchange_code("bad-code")
