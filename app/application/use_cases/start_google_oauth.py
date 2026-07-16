"""Caso de uso para iniciar autorização Google OAuth."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe

from app.domain.ports.oauth_provider import OAuthProvider
from app.domain.ports.repositories import OAuthStateRepository


class StartGoogleOAuth:
    """Gera state aleatório, persiste seu hash e retorna a URL de consentimento."""

    def __init__(
        self,
        state_repository: OAuthStateRepository,
        oauth_provider: OAuthProvider,
        *,
        state_ttl_seconds: int,
    ) -> None:
        self._state_repository = state_repository
        self._oauth_provider = oauth_provider
        self._state_ttl_seconds = state_ttl_seconds

    async def execute(self) -> str:
        """Inicia o fluxo OAuth com proteção anti-CSRF e expiração curta."""

        raw_state = token_urlsafe(32)
        state_hash = sha256(raw_state.encode("utf-8")).hexdigest()
        expires_at = datetime.now(UTC) + timedelta(seconds=self._state_ttl_seconds)
        await self._state_repository.create(state_hash, expires_at)
        return self._oauth_provider.build_authorization_url(raw_state)
