"""Porta para o fluxo OAuth do provedor de e-mail."""

from typing import Protocol

from app.domain.entities.oauth_tokens import OAuthTokenSet


class OAuthProvider(Protocol):
    """Contrato mínimo para iniciar e concluir autorização OAuth."""

    def build_authorization_url(self, state: str) -> str:
        """Cria a URL do consentimento com state anti-CSRF."""
        raise NotImplementedError

    async def exchange_code(self, code: str) -> OAuthTokenSet:
        """Troca um código único por tokens e identifica a conta autorizada."""
        raise NotImplementedError
