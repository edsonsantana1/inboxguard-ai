"""Caso de uso para concluir autorização Google OAuth."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256

from app.core.exceptions import InvalidOAuthStateError
from app.domain.entities.google_account import GoogleAccount
from app.domain.ports.oauth_provider import OAuthProvider
from app.domain.ports.repositories import GoogleAccountRepository, OAuthStateRepository
from app.domain.ports.token_cipher import TokenCipher


class CompleteGoogleOAuth:
    """Valida state, troca o código, criptografa tokens e persiste a conta."""

    def __init__(
        self,
        state_repository: OAuthStateRepository,
        account_repository: GoogleAccountRepository,
        oauth_provider: OAuthProvider,
        token_cipher: TokenCipher,
    ) -> None:
        self._state_repository = state_repository
        self._account_repository = account_repository
        self._oauth_provider = oauth_provider
        self._token_cipher = token_cipher

    async def execute(self, *, state: str, code: str) -> GoogleAccount:
        """Consome o state uma única vez e conclui a conexão da conta."""

        state_hash = sha256(state.encode("utf-8")).hexdigest()
        consumed = await self._state_repository.consume(state_hash, datetime.now(UTC))
        if not consumed:
            raise InvalidOAuthStateError

        token_set = await self._oauth_provider.exchange_code(code)
        existing = await self._account_repository.get_by_email(token_set.email_address)

        encrypted_refresh_token: str | None
        if token_set.refresh_token:
            encrypted_refresh_token = self._token_cipher.encrypt(token_set.refresh_token)
        elif existing is not None:
            encrypted_refresh_token = existing.encrypted_refresh_token
        else:
            encrypted_refresh_token = None

        return await self._account_repository.upsert(
            email_address=token_set.email_address,
            encrypted_access_token=self._token_cipher.encrypt(token_set.access_token),
            encrypted_refresh_token=encrypted_refresh_token,
            token_expires_at=token_set.expires_at,
            scopes=token_set.scopes,
        )
