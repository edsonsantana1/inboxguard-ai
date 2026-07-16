"""Schemas HTTP do fluxo Google OAuth."""

from pydantic import BaseModel


class OAuthConnectionResponse(BaseModel):
    """Confirma a conta conectada sem expor qualquer token."""

    status: str = "connected"
    email_address: str
    message: str = "Conta Gmail conectada com sucesso."
