"""Importa modelos para registro no metadata do SQLAlchemy/Alembic."""

from app.infrastructure.database.models.email_classification import EmailClassificationModel
from app.infrastructure.database.models.email_message import EmailMessageModel
from app.infrastructure.database.models.google_account import GoogleAccountModel
from app.infrastructure.database.models.oauth_state import OAuthStateModel

__all__ = [
    "EmailClassificationModel",
    "EmailMessageModel",
    "GoogleAccountModel",
    "OAuthStateModel",
]
