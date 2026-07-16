#!/usr/bin/env sh
set -eu

# O PostgreSQL já passou pelo health check do Compose; a migração ainda é
# executada antes da API para garantir que o schema esteja na revisão correta.
uv run alembic upgrade head

exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
