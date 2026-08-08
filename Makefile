.PHONY: install dev test lint format check

install:
	uv sync

dev:
	uv run uvicorn backend.app.main:app --reload

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

check:
	uv run ruff check .
	uv run ruff format --check .
	uv run pytest