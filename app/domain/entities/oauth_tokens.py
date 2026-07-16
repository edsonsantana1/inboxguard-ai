"""Dados obtidos ao concluir o fluxo OAuth."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class OAuthTokenSet:
    """Tokens em memória antes da criptografia e persistência."""

    email_address: str
    access_token: str
    refresh_token: str | None
    expires_at: datetime | None
    scopes: tuple[str, ...]
