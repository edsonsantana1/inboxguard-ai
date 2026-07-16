"""Adapter Google OAuth 2.0 para aplicações web server-side."""

from __future__ import annotations

import os
from asyncio import to_thread
from datetime import UTC
from typing import Any

import structlog
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.core.config import Settings
from app.core.exceptions import ConfigurationError, OAuthExchangeError
from app.domain.entities.oauth_tokens import OAuthTokenSet

_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
_TOKEN_URI = "https://oauth2.googleapis.com/token"

logger = structlog.get_logger(__name__)


class GoogleOAuthClient:
    """Inicia consentimento e troca o código sem expor a biblioteca ao domínio."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        if not settings.google_client_id or not settings.google_client_secret:
            raise ConfigurationError(
                "Configure GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET antes do OAuth."
            )
        if not settings.token_encryption_key:
            raise ConfigurationError(
                "Configure TOKEN_ENCRYPTION_KEY antes de armazenar credenciais."
            )
        if settings.google_allow_insecure_http and not settings.is_production:
            os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")

    def _flow(self) -> Flow:
        client_config = {
            "web": {
                "client_id": self._settings.google_client_id,
                "client_secret": self._settings.google_client_secret,
                "auth_uri": _AUTH_URI,
                "token_uri": _TOKEN_URI,
                "redirect_uris": [self._settings.google_redirect_uri],
            }
        }
        flow = Flow.from_client_config(
            client_config,
            scopes=self._settings.google_oauth_scopes,
            autogenerate_code_verifier=False,
        )
        flow.redirect_uri = self._settings.google_redirect_uri
        return flow

    def build_authorization_url(self, state: str) -> str:
        """Cria URL com acesso offline para obter refresh token."""

        flow = self._flow()
        authorization_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            state=state,
        )
        return str(authorization_url)

    async def exchange_code(self, code: str) -> OAuthTokenSet:
        """Troca código e consulta o endereço da conta autorizada."""

        try:
            return await to_thread(self._exchange_code_sync, code)
        except Exception as exc:
            response = getattr(exc, "response", None)
            http_status = getattr(response, "status_code", None)
            if http_status is None:
                http_status = getattr(getattr(exc, "resp", None), "status", None)
            logger.exception(
                "google_oauth_exchange_failed",
                error_type=type(exc).__name__,
                provider_error=getattr(exc, "error", None),
                provider_description=getattr(exc, "description", None),
                http_status=http_status,
            )
            raise OAuthExchangeError from exc

    def _exchange_code_sync(self, code: str) -> OAuthTokenSet:
        flow = self._flow()
        flow.fetch_token(code=code)
        credentials = flow.credentials
        if not credentials.token:
            raise ValueError("O Google não retornou access token.")

        service = build("gmail", "v1", credentials=credentials, cache_discovery=False)
        profile: dict[str, Any] = service.users().getProfile(userId="me").execute()
        email_address = str(profile.get("emailAddress", "")).strip().lower()
        if not email_address:
            raise ValueError("Não foi possível identificar a conta Gmail.")

        expiry = credentials.expiry
        if expiry is not None:
            expiry = expiry.replace(tzinfo=UTC) if expiry.tzinfo is None else expiry.astimezone(UTC)

        scopes = tuple(credentials.scopes or self._settings.google_oauth_scopes)
        return OAuthTokenSet(
            email_address=email_address,
            access_token=str(credentials.token),
            refresh_token=credentials.refresh_token,
            expires_at=expiry,
            scopes=scopes,
        )
