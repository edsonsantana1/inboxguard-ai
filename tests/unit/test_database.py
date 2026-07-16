"""Testes unitários do adaptador de banco sem abrir conexões reais."""

from __future__ import annotations

from types import TracebackType
from typing import Any, cast

import pytest

from app.core.config import Settings
from app.infrastructure.database import session as session_module
from app.infrastructure.database.base import NAMING_CONVENTION, Base
from app.infrastructure.database.session import Database


class FakeConnection:
    """Conexão assíncrona mínima usada pelo teste de ping."""

    def __init__(self) -> None:
        self.executed: list[Any] = []

    async def __aenter__(self) -> FakeConnection:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    async def execute(self, statement: Any) -> None:
        self.executed.append(statement)


class FakeEngine:
    """Engine controlado para testar ping e dispose."""

    def __init__(self) -> None:
        self.connection = FakeConnection()
        self.disposed = False

    def connect(self) -> FakeConnection:
        return self.connection

    async def dispose(self) -> None:
        self.disposed = True


class FakeSession:
    """Sessão controlada para verificar commit e rollback."""

    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> FakeSession:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class FakeSessionFactory:
    """Fábrica compatível com `async_sessionmaker`."""

    def __init__(self, session: FakeSession) -> None:
        self.session = session

    def __call__(self) -> FakeSession:
        return self.session


def build_database(
    monkeypatch: pytest.MonkeyPatch,
    *,
    fake_engine: FakeEngine,
    fake_session: FakeSession,
) -> Database:
    """Cria o adaptador substituindo somente as fábricas externas."""

    monkeypatch.setattr(session_module, "create_async_engine", lambda *args, **kwargs: fake_engine)
    monkeypatch.setattr(
        session_module,
        "async_sessionmaker",
        lambda *args, **kwargs: FakeSessionFactory(fake_session),
    )
    return Database(Settings(database_startup_check=False))


@pytest.mark.asyncio
async def test_ping_executes_select_and_dispose_closes_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = FakeEngine()
    database = build_database(monkeypatch, fake_engine=engine, fake_session=FakeSession())

    latency_ms = await database.ping()
    await database.dispose()

    assert latency_ms >= 0
    assert len(engine.connection.executed) == 1
    assert engine.disposed is True


@pytest.mark.asyncio
async def test_session_commits_after_success(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakeSession()
    database = build_database(monkeypatch, fake_engine=FakeEngine(), fake_session=session)

    async with database.session() as yielded_session:
        assert cast(Any, yielded_session) is session

    assert session.committed is True
    assert session.rolled_back is False


@pytest.mark.asyncio
async def test_session_rolls_back_after_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakeSession()
    database = build_database(monkeypatch, fake_engine=FakeEngine(), fake_session=session)

    with pytest.raises(RuntimeError, match="transaction failed"):
        async with database.session():
            raise RuntimeError("transaction failed")

    assert session.committed is False
    assert session.rolled_back is True


def test_declarative_base_uses_stable_naming_convention() -> None:
    assert Base.metadata.naming_convention == NAMING_CONVENTION
