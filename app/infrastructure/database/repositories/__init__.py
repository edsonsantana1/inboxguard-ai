"""Repositories SQLAlchemy da Fase 2."""

from app.infrastructure.database.repositories.classification_repository import (
    SQLAlchemyEmailClassificationRepository,
)
from app.infrastructure.database.repositories.email_repository import SQLAlchemyEmailRepository
from app.infrastructure.database.repositories.google_account_repository import (
    SQLAlchemyGoogleAccountRepository,
)
from app.infrastructure.database.repositories.oauth_state_repository import (
    SQLAlchemyOAuthStateRepository,
)

__all__ = [
    "SQLAlchemyEmailClassificationRepository",
    "SQLAlchemyEmailRepository",
    "SQLAlchemyGoogleAccountRepository",
    "SQLAlchemyOAuthStateRepository",
]
