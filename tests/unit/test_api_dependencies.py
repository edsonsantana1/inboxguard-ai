"""Testes das dependências HTTP da sessão de banco."""

from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any, cast

import pytest

from app.core.exceptions import ConfigurationError
from app.presentation.api.dependencies import get_session


class FakeSessionProvider:
    @asynccontextmanager
    async def session(self):  # type: ignore[no-untyped-def]
        yield "session"


@pytest.mark.asyncio
async def test_get_session_yields_database_session() -> None:
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(database=FakeSessionProvider()))
    )
    dependency = get_session(request)  # type: ignore[arg-type]

    yielded = await anext(dependency)
    assert cast(Any, yielded) == "session"
    with pytest.raises(StopAsyncIteration):
        await anext(dependency)


@pytest.mark.asyncio
async def test_get_session_rejects_database_without_session_factory() -> None:
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(database=object())))
    dependency = get_session(request)  # type: ignore[arg-type]

    with pytest.raises(ConfigurationError):
        await anext(dependency)
