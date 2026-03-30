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

### Integration Tests

Integration tests require a real PostgreSQL instance.

**Using Docker Compose:**
```bash
docker compose -f docker-compose.test.yml up -d
uv run pytest -m integration
docker compose -f docker-compose.test.yml down
```

**Custom database URL:**
```bash
TEST_DATABASE_URL=postgresql://user:pass@host:5432/dbname uv run pytest -m integration
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

## API Endpoints

| Method | Path | Description | Status Code |
|--------|------|-------------|-------------|
| `GET` | `/health` | Health check | 200 |
| `POST` | `/users` | Register a new user | 201 |
| `POST` | `/users/{user_id}/activation-code` | Send 4-digit activation code | 201 |
| `POST` | `/users/activate` | Activate account (Basic Auth + code) | 200 |

### `POST /users`

Register a new user with email and password.

**Request body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "lang": "fr"
}
```

`lang` is required. Supported values: `fr`, `en`, `es`, `it`, `de`.

**Response (201):**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "is_active": false,
  "lang": "fr",
  "created_at": "2026-03-30T12:00:00Z"
}
```

**Errors:**
- `409` — Email already registered (`USER_ALREADY_EXISTS`)
- `422` — Validation error (invalid email, password too short, unsupported lang)

### `POST /users/{user_id}/activation-code`

Generate and send a 4-digit activation code by email. Code expires after 1 minute.

**Response (201):**
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "expires_at": "2026-03-30T12:01:00Z"
}
```

**Errors:**
- `404` — User not found (`USER_NOT_FOUND`)

### `POST /users/activate`

Activate a user account with HTTP Basic Auth and a 4-digit activation code.

**Authentication:** HTTP Basic Auth (email as username, password as password).

**Request body:**
```json
{
  "code": "1234"
}
```

**Response (200):**
```json
{
  "detail": "Account activated successfully"
}
```

**Errors:**
- `400` — Invalid activation code (`INVALID_ACTIVATION_CODE`)
- `400` — Activation code expired (`ACTIVATION_CODE_EXPIRED`)
- `401` — Invalid credentials (wrong email or password)
- `422` — Validation error (code must be exactly 4 digits)

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
