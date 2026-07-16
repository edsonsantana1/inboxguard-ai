"""Criação do engine, fábrica de sessões e verificação de conectividade."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings


class Database:
    """Gerencia o ciclo de vida da conexão assíncrona com o PostgreSQL."""

    def __init__(self, settings: Settings) -> None:
        connect_args = {"timeout": settings.database_connect_timeout_seconds}
        self._engine: AsyncEngine = create_async_engine(
            settings.database_url,
            echo=settings.database_echo,
            pool_pre_ping=True,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            connect_args=connect_args,
        )
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Fornece uma sessão transacional e garante rollback em falhas."""

        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def ping(self) -> float:
        """Executa uma consulta mínima e retorna a latência em milissegundos."""

        started_at = perf_counter()
        async with self._engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return round((perf_counter() - started_at) * 1000, 2)

    async def dispose(self) -> None:
        """Fecha o pool de conexões durante o encerramento da aplicação."""

        await self._engine.dispose()
