"""Testes HTTP do tratamento centralizado de exceções."""

from __future__ import annotations

from fastapi import Query
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.exceptions import (
    ConfigurationError,
    InboxGuardError,
    ResourceNotFoundError,
)
from app.presentation.api.application import create_app
from tests.conftest import FakeDatabase


def build_client() -> TestClient:
    """Cria aplicação com rotas de teste e sem serviços externos."""

    settings = Settings(
        environment="test",
        database_startup_check=False,
        allowed_hosts=["testserver"],
        log_level="WARNING",
    )
    app = create_app(settings=settings, database=FakeDatabase())

    @app.get("/test/controlled-error")
    async def controlled_error() -> None:
        raise InboxGuardError("Operação inválida", code="invalid_operation")

    @app.get("/test/unexpected-error")
    async def unexpected_error() -> None:
        raise RuntimeError("internal secret detail")

    @app.get("/test/validation")
    async def validation(value: int = Query(ge=1)) -> dict[str, int]:
        return {"value": value}

    return TestClient(app, raise_server_exceptions=False)


def test_controlled_error_uses_standard_envelope() -> None:
    with build_client() as client:
        response = client.get("/test/controlled-error")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_operation"
    assert response.json()["request_id"]


def test_validation_error_does_not_expose_framework_details_as_message() -> None:
    with build_client() as client:
        response = client.get("/test/validation", params={"value": 0})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["details"]


def test_unexpected_error_is_not_leaked_to_client() -> None:
    with build_client() as client:
        response = client.get("/test/unexpected-error")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_server_error"
    assert "internal secret detail" not in response.text


def test_configuration_error_returns_503() -> None:
    settings = Settings(
        environment="test",
        database_startup_check=False,
        allowed_hosts=["testserver"],
        log_level="WARNING",
    )
    app = create_app(settings=settings, database=FakeDatabase())

    @app.get("/test/configuration-error")
    async def configuration_error() -> None:
        raise ConfigurationError("Configuração ausente")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/test/configuration-error")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "configuration_error"


def test_not_found_error_returns_404() -> None:
    settings = Settings(
        environment="test",
        database_startup_check=False,
        allowed_hosts=["testserver"],
        log_level="WARNING",
    )
    app = create_app(settings=settings, database=FakeDatabase())

    @app.get("/test/not-found")
    async def not_found() -> None:
        raise ResourceNotFoundError("E-mail")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/test/not-found")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
