"""Contratos técnicos usados pela camada de apresentação."""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession


class DatabaseLifecycle(Protocol):
    """Contrato mínimo para verificar e encerrar a conexão com o banco."""

    async def ping(self) -> float:
        """Retorna a latência do banco em milissegundos."""
        raise NotImplementedError

    async def dispose(self) -> None:
        """Libera o pool e os recursos associados ao engine."""
        raise NotImplementedError


class DatabaseSessionProvider(Protocol):
    """Contrato para abrir sessões transacionais assíncronas."""

    def session(self) -> AbstractAsyncContextManager[AsyncSession]:
        """Retorna um gerenciador de contexto de sessão."""
        raise NotImplementedError
