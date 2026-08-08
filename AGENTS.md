# RelayAI Engineering Guidelines

## Project

RelayAI is an AI inference gateway for voice AI platforms.

The system sits between Speech-to-Text (STT) and Large Language Models (LLMs)
and determines whether an incoming request can be handled without an LLM.

## Architecture Principles

- Keep the system provider-agnostic.
- Keep the core domain independent of FastAPI.
- Keep infrastructure concerns outside the domain.
- Prefer small, composable modules.
- Do not introduce unnecessary frameworks.
- Optimize for low latency.

## Python

- Python 3.12+
- Type hints are required.
- Use async APIs for I/O.
- Follow PEP 8.
- Use Ruff for linting and formatting.

## API

- FastAPI.
- Pydantic models for request and response validation.
- Version public APIs under `/v1`.

## Database

- PostgreSQL.
- SQLAlchemy 2.x.
- Async database access.
- Alembic for migrations.

## Cache

- Redis for short-lived state and hot data.
- Do not use Redis as permanent storage.

## Testing

Every feature must have tests.

Run:

    make check

before considering a feature complete.

## Git

Use small, focused commits.

Commit format:

    <type>(<scope>): <description>

Examples:

    feat(api): add chat endpoint
    feat(intent): add greeting intent
    fix(redis): handle expired conversation
    chore(project): bootstrap repository

Do not commit:

- secrets
- `.env` files
- virtual environments
- IDE configuration
- generated Python files
- cache directories

## Product Principle

The LLM should be the last resort.

RelayAI should first determine whether a request can be handled by:

1. deterministic rules,
2. conversation context,
3. reusable knowledge,
4. semantic matching,
5. other low-cost mechanisms,

before forwarding the request to an LLM.