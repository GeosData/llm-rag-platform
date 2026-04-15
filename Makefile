.PHONY: dev down test lint format type-check migrate migration

dev:
	docker compose up --build

down:
	docker compose down

test:
	python -m pytest

lint:
	python -m ruff check app tests

format:
	python -m ruff format app tests

type-check:
	python -m mypy app

migrate:
	python -m alembic upgrade head

migration:
	python -m alembic revision --autogenerate -m "$(msg)"
