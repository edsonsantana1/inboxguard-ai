"""Fixtures compartilhadas pelos testes."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.presentation.api.application import create_app


@pytest.fixture(autouse=True)
def isolate_test_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[None]:
    """Impede que testes carreguem credenciais reais do ambiente ou `.env`."""

    # Desativa a leitura automática do arquivo .env durante os testes.
    monkeypatch.setitem(
        Settings.model_config,
        "env_file",
        None,
    )

    # Remove do processo de teste todas as variáveis correspondentes
    # aos campos de configuração da aplicação.
    for field_name in Settings.model_fields:
        monkeypatch.delenv(
            field_name.upper(),
            raising=False,
        )

    # Evita que configurações carregadas em outro teste permaneçam no cache.
    get_settings.cache_clear()

    yield

    get_settings.cache_clear()


class FakeDatabase:
    """Substituto controlável que impede acesso a serviços externos nos testes."""

    def __init__(
        self,
        *,
        latency_ms: float = 1.25,
        error: Exception | None = None,
    ) -> None:
        self.latency_ms = latency_ms
        self.error = error
        self.disposed = False
        self.ping_calls = 0

    async def ping(self) -> float:
        """Simula a verificação de disponibilidade do banco."""

        self.ping_calls += 1

        if self.error is not None:
            raise self.error

        return self.latency_ms

    async def dispose(self) -> None:
        """Registra que a conexão simulada foi encerrada."""

        self.disposed = True


@pytest.fixture
def test_settings() -> Settings:
    """Configuração isolada e determinística para testes."""

    return Settings(
        environment="test",
        database_startup_check=False,
        allowed_hosts=["testserver"],
        log_level="WARNING",
    )


@pytest.fixture
def fake_database() -> FakeDatabase:
    """Banco saudável usado como padrão na suíte."""

    return FakeDatabase()


@pytest.fixture
def client(
    test_settings: Settings,
    fake_database: FakeDatabase,
) -> Iterator[TestClient]:
    """Cliente HTTP que executa corretamente o ciclo de vida da aplicação."""

    app = create_app(
        settings=test_settings,
        database=fake_database,
    )

    with TestClient(app) as test_client:
        yield test_client
