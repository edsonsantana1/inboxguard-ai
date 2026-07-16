"""Testes das exceções controladas da aplicação."""

from app.core.exceptions import DatabaseUnavailableError, InboxGuardError


def test_application_error_preserves_safe_code_and_message() -> None:
    error = InboxGuardError("Falha esperada", code="expected_failure")
    assert error.message == "Falha esperada"
    assert error.code == "expected_failure"
    assert str(error) == "Falha esperada"


def test_database_unavailable_error_has_fixed_safe_message() -> None:
    error = DatabaseUnavailableError()
    assert error.code == "database_unavailable"
    assert "não está disponível" in error.message
