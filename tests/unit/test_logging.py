"""Testes do mascaramento aplicado ao logging estruturado."""

from __future__ import annotations

from typing import Any, cast

from app.core.logging import REDACTED, redact_sensitive_data


def test_sensitive_values_are_redacted_recursively() -> None:
    event = {
        "event": "external_call",
        "authorization": "Bearer secret",
        "payload": {
            "refresh_token": "token-value",
            "safe_field": "visible",
            "items": [{"api_key": "secret-key"}],
        },
    }

    result = redact_sensitive_data(None, "info", event)
    payload = cast(dict[str, Any], result["payload"])
    items = cast(list[dict[str, Any]], payload["items"])

    assert result["authorization"] == REDACTED
    assert payload["refresh_token"] == REDACTED
    assert payload["safe_field"] == "visible"
    assert items[0]["api_key"] == REDACTED


def test_tuple_values_are_preserved_while_nested_secrets_are_redacted() -> None:
    event = {"items": ({"password": "secret"},)}
    result = redact_sensitive_data(None, "info", event)
    assert result["items"] == ({"password": REDACTED},)
