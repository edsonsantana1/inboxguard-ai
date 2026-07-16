"""Entidade de conta Google autorizada."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GoogleAccount:
    """Credenciais persistidas de uma conta, sempre criptografadas em repouso."""

    id: UUID
    email_address: str
    encrypted_access_token: str
    encrypted_refresh_token: str | None
    token_expires_at: datetime | None
    scopes: tuple[str, ...]
    created_at: datetime
    updated_at: datetime
