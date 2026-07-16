"""Testes da criptografia de tokens OAuth."""

import pytest
from cryptography.fernet import Fernet

from app.core.exceptions import ConfigurationError
from app.infrastructure.security import FernetTokenCipher


def test_fernet_cipher_round_trip() -> None:
    cipher = FernetTokenCipher(Fernet.generate_key().decode())
    encrypted = cipher.encrypt("refresh-token")

    assert encrypted != "refresh-token"
    assert cipher.decrypt(encrypted) == "refresh-token"


def test_invalid_fernet_key_is_rejected() -> None:
    with pytest.raises(ConfigurationError, match="Fernet"):
        FernetTokenCipher("invalid-key")


def test_cipher_rejects_token_from_another_key() -> None:
    first = FernetTokenCipher(Fernet.generate_key().decode())
    second = FernetTokenCipher(Fernet.generate_key().decode())

    with pytest.raises(ConfigurationError, match="descriptografar"):
        second.decrypt(first.encrypt("secret"))
