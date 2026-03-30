# User Registration API

User registration API with email verification, built with FastAPI and PostgreSQL.

## Tech Stack

- **Language**: Python 3.13
- **Framework**: FastAPI
- **Database**: PostgreSQL 17 (raw SQL with asyncpg, no ORM)
- **Package Manager**: uv
- **Containerization**: Docker + docker-compose

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed diagrams and layer descriptions.

This project follows **hexagonal architecture** (ports & adapters):

```
src/app/
├── api/              # Inbound adapters (HTTP routes, request/response models)
│   └── middlewares/  # Request logging, correlation IDs
├── core/             # Configuration, logging, shared exceptions
├── domain/           # Business logic, domain models, port interfaces
├── infrastructure/   # Outbound adapters (database, email service)
└── main.py           # Application entry point, lifespan events
```

- **Domain layer** defines business rules and port interfaces
- **API layer** handles HTTP concerns and delegates to domain services
- **Infrastructure layer** implements ports (database repositories, email clients)
- **Dependencies flow inward**: API -> Domain <- Infrastructure

See [FEATURES.md](FEATURES.md) for the full feature inventory and status.

## Prerequisites

- Docker
- docker-compose

No local Python installation required.

## Getting Started

### Run with Docker

```bash
docker-compose up --build
```

The API is available at http://localhost:8000

API documentation: http://localhost:8000/docs

### Local Development

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync --dev

# Install pre-commit hooks
uv run pre-commit install

# Run the app
uv run uvicorn app.main:app --reload
```

### Run Tests

```bash
uv run pytest
```

### Code Quality

```bash
# Linting
uv run ruff check src/ tests/

# Formatting check
uv run ruff format --check src/ tests/

# Type checking
uv run mypy
```

## Project Structure

```
.
├── src/app/              # Application source code
│   ├── api/              # API routers and schemas
│   ├── core/             # Config, settings, exceptions
│   ├── domain/           # Domain models and business logic
│   ├── infrastructure/   # Database and external services
│   └── main.py           # FastAPI app entry point
├── tests/                # Test suite
├── docker-compose.yml    # Multi-container setup
├── Dockerfile            # Multi-stage production build
└── pyproject.toml        # Project config and dependencies
```
