.PHONY: install run test test-cov lint format type-check quality migrate revision docker-up docker-down

install:
	uv sync --group dev

run:
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	uv run pytest

test-cov:
	uv run pytest --cov=app --cov-report=term-missing --cov-report=html

lint:
	uv run ruff check .

format:
	uv run ruff format .
	uv run ruff check . --fix

type-check:
	uv run mypy app tests

quality: lint type-check test-cov

migrate:
	uv run alembic upgrade head

revision:
	@test -n "$(name)" || (echo "Use: make revision name=descricao_da_migracao" && exit 1)
	uv run alembic revision --autogenerate -m "$(name)"

docker-up:
	docker compose up --build

docker-down:
	docker compose down
