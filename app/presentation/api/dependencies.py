"""Dependências compartilhadas pelos endpoints da API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import cast

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import ConfigurationError
from app.core.protocols import DatabaseLifecycle, DatabaseSessionProvider


def get_settings_from_request(request: Request) -> Settings:
    """Obtém as configurações associadas à instância atual da aplicação."""

    return cast(Settings, request.app.state.settings)


def get_database(request: Request) -> DatabaseLifecycle:
    """Obtém o adaptador de banco associado à aplicação."""

    return cast(DatabaseLifecycle, request.app.state.database)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Abre uma sessão transacional para a requisição atual."""

    database = request.app.state.database
    if not hasattr(database, "session"):
        raise ConfigurationError("O adaptador de banco não fornece sessões.")

    session_provider = cast(DatabaseSessionProvider, database)
    async with session_provider.session() as session:
        yield session
