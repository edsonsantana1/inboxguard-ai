# Migrações

A infraestrutura do Alembic está configurada para PostgreSQL assíncrono. A Fase 1 não cria tabelas de negócio artificialmente; as primeiras revisões serão geradas quando as entidades persistentes forem introduzidas na Fase 2.

Comandos:

```bash
uv run alembic revision --autogenerate -m "descricao"
uv run alembic upgrade head
uv run alembic downgrade -1
```

Toda migração gerada automaticamente deve ser revisada antes de ser aplicada.
