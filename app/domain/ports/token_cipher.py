"""Porta de criptografia de segredos persistidos."""

from typing import Protocol


class TokenCipher(Protocol):
    """Criptografa tokens sem expor a implementação ao caso de uso."""

    def encrypt(self, plaintext: str) -> str:
        """Criptografa um valor em memória."""
        raise NotImplementedError

    def decrypt(self, ciphertext: str) -> str:
        """Descriptografa um valor apenas quando necessário."""
        raise NotImplementedError
