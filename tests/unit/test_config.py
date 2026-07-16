"""Testes das configurações tipadas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings


def test_log_level_is_normalized() -> None:
    settings = Settings(log_level="debug")
    assert settings.log_level == "DEBUG"


def test_invalid_log_level_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(log_level="verbose")


def test_comma_separated_allowed_hosts_are_supported() -> None:
    settings = Settings(allowed_hosts="localhost, api.internal")
    assert settings.allowed_hosts == ["localhost", "api.internal"]


def test_database_pool_size_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        Settings(database_pool_size=0)


def test_get_settings_returns_cached_instance() -> None:
    get_settings.cache_clear()
    first = get_settings()
    second = get_settings()
    assert first is second
    get_settings.cache_clear()


def test_blank_optional_secrets_become_none() -> None:
    settings = Settings(google_client_id="", token_encryption_key="")
    assert settings.google_client_id is None
    assert settings.token_encryption_key is None


def test_google_oauth_requires_readonly_scope_in_phase_two() -> None:
    with pytest.raises(ValidationError):
        Settings(google_oauth_scopes=["https://mail.google.com/"])


def test_google_oauth_configuration_flag_requires_all_secrets() -> None:
    incomplete = Settings(google_client_id="client")
    complete = Settings(
        google_client_id="client",
        google_client_secret="secret",
        token_encryption_key="ZmFrZS1rZXktdGhhdC1pcy1ub3QtcmVhbC0xMjM0NQ==",
    )

    assert incomplete.google_oauth_configured is False
    assert complete.google_oauth_configured is True
