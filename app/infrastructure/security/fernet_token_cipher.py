"""Implementação Fernet para criptografia autenticada de tokens."""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.core.exceptions import ConfigurationError


class FernetTokenCipher:
    """Protege access e refresh tokens antes da persistência."""

    def __init__(self, key: str) -> None:
        try:
            self._fernet = Fernet(key.encode("utf-8"))
        except (TypeError, ValueError) as exc:
            raise ConfigurationError("TOKEN_ENCRYPTION_KEY não é uma chave Fernet válida.") from exc

    def encrypt(self, plaintext: str) -> str:
        """Criptografa texto e retorna um token serializável."""

        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        """Descriptografa um token autenticado."""

        try:
            return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise ConfigurationError(
                "Não foi possível descriptografar as credenciais armazenadas."
            ) from exc
