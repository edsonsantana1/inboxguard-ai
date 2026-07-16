"""Testes HTTP dos endpoints operacionais."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.presentation.api.application import create_app
from tests.conftest import FakeDatabase


def test_health_returns_service_metadata(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["service"] == "InboxGuard AI"
    assert response.json()["environment"] == "test"
    assert response.headers["X-Request-ID"]


def test_request_id_is_preserved(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Request-ID": "trace-123"})
    assert response.headers["X-Request-ID"] == "trace-123"


def test_ready_returns_database_latency(client: TestClient) -> None:
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["database"] == "available"
    assert response.json()["latency_ms"] == 1.25


def test_ready_returns_503_when_database_is_unavailable(test_settings: Settings) -> None:
    database = FakeDatabase(error=ConnectionError("database offline"))
    app = create_app(settings=test_settings, database=database)

    with TestClient(app) as client:
        response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["database"] == "unavailable"
    assert "database offline" not in response.text


def test_database_is_disposed_after_lifespan(test_settings: Settings) -> None:
    database = FakeDatabase()
    app = create_app(settings=test_settings, database=database)

    with TestClient(app):
        assert database.disposed is False

    assert database.disposed is True


def test_startup_database_check_runs_when_enabled() -> None:
    settings = Settings(
        environment="test",
        database_startup_check=True,
        allowed_hosts=["testserver"],
        log_level="WARNING",
    )
    database = FakeDatabase(latency_ms=2.5)
    app = create_app(settings=settings, database=database)

    with TestClient(app):
        pass

    assert database.ping_calls == 1


def test_startup_database_failure_does_not_crash_liveness() -> None:
    settings = Settings(
        environment="test",
        database_startup_check=True,
        allowed_hosts=["testserver"],
        log_level="WARNING",
    )
    database = FakeDatabase(error=ConnectionError("offline"))
    app = create_app(settings=settings, database=database)

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert database.ping_calls == 1
