"""Logging estruturado com mascaramento de informações sensíveis."""

from __future__ import annotations

import logging
import sys
from collections.abc import Mapping, MutableMapping
from typing import Any, cast

import structlog

from app.core.config import Settings

SENSITIVE_KEY_PARTS = (
    "authorization",
    "body_text",
    "client_secret",
    "cookie",
    "password",
    "refresh_token",
    "secret",
    "token",
    "api_key",
)
REDACTED = "***redacted***"


def _is_sensitive_key(key: str) -> bool:
    """Identifica chaves que não devem aparecer em logs."""

    normalized = key.lower()
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def _redact(value: Any) -> Any:
    """Mascara recursivamente valores associados a chaves sensíveis."""

    if isinstance(value, Mapping):
        return {
            str(key): REDACTED if _is_sensitive_key(str(key)) else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact(item) for item in value)
    return value


def redact_sensitive_data(
    _logger: Any,
    _method_name: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """Processor do Structlog que remove segredos antes da renderização."""

    return cast(MutableMapping[str, Any], _redact(event_dict))


def configure_logging(settings: Settings) -> None:
    """Configura logging JSON em produção e legível durante desenvolvimento."""

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level),
        force=True,
    )

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        redact_sensitive_data,
    ]

    processors: list[Any]
    if settings.is_production:
        processors = [
            *shared_processors,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # ConsoleRenderer já renderiza exceções; format_exc_info duplicaria o trabalho.
        processors = [*shared_processors, structlog.dev.ConsoleRenderer(colors=False)]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
