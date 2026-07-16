"""Adapters Google OAuth e Gmail."""

from app.infrastructure.gmail.gmail_client import GmailClient
from app.infrastructure.gmail.google_oauth_client import GoogleOAuthClient

__all__ = ["GmailClient", "GoogleOAuthClient"]
