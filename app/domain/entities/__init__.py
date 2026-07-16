"""Entidades de domínio do InboxGuard AI."""

from app.domain.entities.email_message import EmailMessage
from app.domain.entities.google_account import GoogleAccount
from app.domain.entities.oauth_tokens import OAuthTokenSet
from app.domain.entities.sync_result import SyncResult

__all__ = ["EmailMessage", "GoogleAccount", "OAuthTokenSet", "SyncResult"]
