"""Gera uma chave Fernet compatível usando apenas a biblioteca padrão."""

from __future__ import annotations

import base64
import secrets


def generate_fernet_key() -> str:
    """Retorna 32 bytes aleatórios codificados em base64 URL-safe."""

    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")


if __name__ == "__main__":
    print(generate_fernet_key())
