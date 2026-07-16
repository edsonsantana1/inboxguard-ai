"""Testes da política de retentativas do adapter Gmail."""

from types import SimpleNamespace

from googleapiclient.errors import HttpError

from app.infrastructure.gmail.gmail_client import _is_recoverable


def http_error(status: int) -> HttpError:
    response = SimpleNamespace(status=status, reason="reason")
    return HttpError(response, b"{}")


def test_retry_policy_accepts_only_transient_failures() -> None:
    assert _is_recoverable(http_error(429)) is True
    assert _is_recoverable(http_error(503)) is True
    assert _is_recoverable(http_error(401)) is False
    assert _is_recoverable(TimeoutError()) is True
    assert _is_recoverable(ValueError()) is False
