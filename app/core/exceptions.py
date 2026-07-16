"""Exceções controladas e independentes do framework web."""

from __future__ import annotations


class InboxGuardError(Exception):
    """Erro esperado da aplicação que pode ser apresentado de forma segura."""

    def __init__(self, message: str, *, code: str = "application_error") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class DatabaseUnavailableError(InboxGuardError):
    """Indica que o banco não respondeu ao teste de prontidão."""

    def __init__(self) -> None:
        super().__init__(
            "O banco de dados não está disponível.",
            code="database_unavailable",
        )


class ConfigurationError(InboxGuardError):
    """Indica ausência ou inconsistência de configuração obrigatória."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="configuration_error")


class InvalidOAuthStateError(InboxGuardError):
    """Indica state OAuth inexistente, expirado ou já consumido."""

    def __init__(self) -> None:
        super().__init__(
            "A autorização expirou ou já foi utilizada. Inicie o fluxo novamente.",
            code="invalid_oauth_state",
        )


class OAuthDeniedError(InboxGuardError):
    """Indica que o usuário ou o provedor recusou a autorização."""

    def __init__(self) -> None:
        super().__init__(
            "A autorização do Google foi cancelada ou recusada.",
            code="oauth_denied",
        )


class ExternalServiceError(InboxGuardError):
    """Representa falha segura de um serviço externo."""

    def __init__(self, service: str) -> None:
        super().__init__(
            f"O serviço {service} está temporariamente indisponível.",
            code="external_service_unavailable",
        )


class ResourceNotFoundError(InboxGuardError):
    """Indica que um recurso solicitado não existe."""

    def __init__(self, resource: str) -> None:
        super().__init__(f"{resource} não encontrado.", code="not_found")


class GmailAccountNotConnectedError(InboxGuardError):
    """Indica que nenhuma conta Gmail foi autorizada."""

    def __init__(self) -> None:
        super().__init__(
            "Nenhuma conta Gmail está conectada. Acesse /auth/google/start primeiro.",
            code="gmail_account_not_connected",
        )


class OAuthExchangeError(InboxGuardError):
    """Indica falha ao trocar ou validar o código OAuth."""

    def __init__(self) -> None:
        super().__init__(
            "Não foi possível concluir a autorização do Google.",
            code="oauth_exchange_failed",
        )
