"""Carregamento tipado das configurações do ambiente."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "test", "staging", "production"]
AIProviderName = Literal["openai", "groq", "disabled"]
GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"


class Settings(BaseSettings):
    """Configurações centrais carregadas de variáveis de ambiente e `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "InboxGuard AI"
    app_version: str = "0.3.0"
    environment: Environment = "development"
    debug: bool = False
    log_level: str = "INFO"
    allowed_hosts: list[str] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "testserver"]
    )

    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+asyncpg://inboxguard:inboxguard@localhost:5432/inboxguard"
    database_echo: bool = False
    database_pool_size: int = Field(default=5, ge=1, le=50)
    database_max_overflow: int = Field(default=10, ge=0, le=100)
    database_connect_timeout_seconds: float = Field(default=5.0, gt=0, le=60)
    database_startup_check: bool = True

    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"
    google_oauth_scopes: list[str] = Field(default_factory=lambda: [GMAIL_READONLY_SCOPE])
    google_oauth_state_ttl_seconds: int = Field(default=600, ge=60, le=3600)
    google_allow_insecure_http: bool = True

    token_encryption_key: str | None = None
    gmail_sync_max_messages: int = Field(default=50, ge=1, le=500)
    gmail_store_body_text: bool = False
    gmail_retry_attempts: int = Field(default=3, ge=1, le=8)

    ai_provider: AIProviderName = "openai"
    ai_deterministic_threshold: float = Field(default=0.88, ge=0, le=1)
    ai_timeout_seconds: float = Field(default=30.0, gt=0, le=120)
    ai_retry_attempts: int = Field(default=3, ge=1, le=6)
    ai_max_input_characters: int = Field(default=12000, ge=500, le=50000)
    ai_prompt_version: str = "email-classification-v1"
    openai_api_key: str | None = None
    openai_model: str = "gpt-5-mini"

    groq_api_key: str | None = None
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "openai/gpt-oss-20b"

    # Permanecem reservadas para fases posteriores.
    telegram_bot_token: str | None = None
    telegram_allowed_user_ids: list[int] = Field(default_factory=list)
    telegram_allowed_chat_ids: list[int] = Field(default_factory=list)
    telegram_webhook_secret: str | None = None

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        """Normaliza e valida o nível de log aceito pela biblioteca padrão."""

        normalized = value.upper()
        allowed = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
        if normalized not in allowed:
            message = f"LOG_LEVEL deve ser um destes valores: {sorted(allowed)}"
            raise ValueError(message)
        return normalized

    @field_validator("allowed_hosts", "google_oauth_scopes", mode="before")
    @classmethod
    def parse_string_lists(cls, value: object) -> object:
        """Aceita lista JSON ou uma lista simples separada por vírgulas."""

        if isinstance(value, str) and not value.lstrip().startswith("["):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator(
        "google_client_id",
        "google_client_secret",
        "token_encryption_key",
        "openai_api_key",
        "groq_api_key",
        "telegram_bot_token",
        "telegram_webhook_secret",
        mode="before",
    )
    @classmethod
    def empty_string_to_none(cls, value: object) -> object:
        """Trata variáveis vazias do `.env` como ausentes."""

        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("google_oauth_scopes")
    @classmethod
    def require_readonly_gmail_scope(cls, value: list[str]) -> list[str]:
        """Impede que a Fase 2 solicite permissões além de leitura."""

        if value != [GMAIL_READONLY_SCOPE]:
            raise ValueError(
                "A Fase 2 deve utilizar somente o escopo gmail.readonly. "
                "Permissões de rascunho e envio pertencem à Fase 5."
            )
        return value

    @property
    def is_production(self) -> bool:
        """Indica se a aplicação está executando no ambiente de produção."""

        return self.environment == "production"

    @property
    def ai_configured(self) -> bool:
        """Indica se o provedor de IA selecionado possui credencial."""

        if self.ai_provider == "openai":
            return bool(self.openai_api_key)

        if self.ai_provider == "groq":
            return bool(self.groq_api_key)

        return False

    @property
    def google_oauth_configured(self) -> bool:
        """Indica se as credenciais mínimas do Google foram fornecidas."""

        return bool(
            self.google_client_id
            and self.google_client_secret
            and self.google_redirect_uri
            and self.token_encryption_key
        )


@lru_cache
def get_settings() -> Settings:
    """Retorna uma instância cacheada para evitar releituras do ambiente."""

    return Settings()
