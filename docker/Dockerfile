FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# O uv é instalado com faixa de versão controlada para evitar mudanças de major version.
RUN pip install --no-cache-dir "uv>=0.10,<1.0"

WORKDIR /app

# Copiar os arquivos de dependência primeiro mantém o cache de build eficiente.
COPY pyproject.toml README.md ./
RUN uv sync --no-dev --no-install-project

COPY . .
RUN chmod +x docker/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./docker/entrypoint.sh"]
