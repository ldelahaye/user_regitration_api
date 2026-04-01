# User Registration API

User registration API with email verification, built with FastAPI and PostgreSQL.

### How it works

```mermaid
sequenceDiagram
    actor Client
    participant API
    participant DB as Database
    participant Email as Email Service

    Client->>API: POST /users (email, password, lang)
    API->>DB: INSERT user + activation code
    API->>Email: Send 4-digit code
    API-->>Client: 201 Created

    Note over Client,Email: User reads the 4-digit code from email (valid 1 min)

    Client->>API: POST /users/activate (Basic Auth + code)
    API->>DB: Verify credentials + validate code
    API->>DB: Activate user
    API-->>Client: 200 OK

    Client->>API: GET /users/me (Basic Auth)
    API->>DB: Verify credentials + fetch user
    API-->>Client: 200 OK (user data)
```

## Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Hexagonal architecture, layer diagram, data flow |
| [FEATURES.md](FEATURES.md) | Feature inventory with status and key files |
| [.env.example](.env.example) | All environment variables with defaults and descriptions |

## Tech Stack

- **Language**: Python 3.14
- **Framework**: FastAPI
- **Database**: PostgreSQL 17 (raw SQL with asyncpg, no ORM)
- **Package Manager**: uv
- **Containerization**: Docker + Docker Compose
- **CI/CD**: GitHub Actions (lint, test, security scan, container build)

## Quick Start

### Prerequisites

- Docker
- Docker Compose

No local Python installation required.

### 1. Clone and configure

```bash
git clone https://github.com/ldelahaye/user-registration-api.git
cd user-registration-api
cp .env.example .env
```

Edit `.env` and set `APP_HMAC_SECRET` to a random value. See [`.env.example`](.env.example) for all available variables.

### 2. Start

```bash
docker compose up --build
```

The app waits for PostgreSQL to be healthy, runs database migrations automatically, then starts.

The default port is `8000` (configurable via `APP_PORT` in `.env`).

| Resource | URL |
|----------|-----|
| Swagger UI | http://localhost:8000/docs |
| Health check | http://localhost:8000/health |

### 3. Stop

```bash
docker compose down
```

To also remove the database volume:

```bash
docker compose down -v
```

## Tests

Requires Docker only — no local Python installation needed.

```bash
# Run integration tests
docker compose -f docker-compose.test.yml run --rm app-test uv run pytest -m integration

# Tear down
docker compose -f docker-compose.test.yml down
```

## Local Development

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync --dev

# Install pre-commit hooks
uv run pre-commit install

# Run the app
uv run uvicorn app.main:app --reload

# Unit tests
uv run pytest

# Integration tests (requires test database running)
docker compose -f docker-compose.test.yml up -d
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5433/registration_test uv run pytest -m integration
docker compose -f docker-compose.test.yml down
```

### Code Quality

```bash
uv run ruff check src/ tests/    # Linting
uv run ruff format --check src/ tests/  # Formatting
uv run mypy                      # Type checking
```

## CI/CD

Three GitHub Actions workflows run on push and pull requests to `main`:

| Workflow | Description |
|----------|-------------|
| **CI** (`ci.yml`) | Lint (ruff, mypy), unit tests with coverage, integration tests, container build and push to GHCR |
| **Security** (`security.yml`) | Dependency audit (pip-audit), Docker image scan (Grype) |
| **CodeQL** (`codeql.yml`) | Weekly static analysis |

[Dependabot](.github/dependabot.yml) keeps pip, GitHub Actions, and Docker dependencies up to date.

## API Endpoints

| Method | Path | Auth | Description | Status Code |
|--------|------|------|-------------|-------------|
| `GET` | `/health` | — | Health check (database + email) | 200 / 503 |
| `POST` | `/users` | — | Register a new user (auto-sends activation code) | 201 / 502 |
| `POST` | `/users/activation-code` | — | Re-request activation code by email | 201 |
| `POST` | `/users/activate` | Basic Auth | Activate account with 4-digit code | 200 |
| `GET` | `/users/me` | Basic Auth | Get current user info (active accounts only) | 200 |

Full request/response documentation is available in Swagger UI at `/docs`.

### Registration flow

1. `POST /users` with email, password, and lang (`fr`, `en`, `es`, `it`, `de`) — creates the account and sends an activation code by email. If the email service is unavailable, the request fails with 502 and the user is not created (transaction rollback).
2. Retrieve the 4-digit activation code from the email (in dev mode with `APP_EMAIL_MOCK=true`, the code is visible in the container logs).
3. `POST /users/activate` with Basic Auth (email + password) and the code — activates the account.
4. `GET /users/me` with Basic Auth — returns user info (requires an active account).

A new code can be re-requested via `POST /users/activation-code`. After too many failed attempts, the code is locked (429).

### Password policy

Minimum 12 characters with uppercase, lowercase, digit, and special character. These defaults follow [ANSSI R22](https://cyber.gouv.fr/publications/recommandations-relatives-lauthentification-multifacteur-et-aux-mots-de-passe) (minimum entropy of 80 bits for user-chosen passwords). All rules are configurable via environment variables (see `.env.example`).

## Project Structure

```
.
├── .github/workflows/    # CI/CD pipelines (lint, test, security, build)
├── docs/                 # Additional documentation
├── src/app/              # Application source code
│   ├── api/              # API routers, schemas, middlewares
│   ├── core/             # Config, settings, exceptions
│   ├── domain/           # Domain models and business logic
│   ├── infrastructure/   # Database, email, migrations
│   └── main.py           # FastAPI app entry point
├── tests/                # Unit and integration tests
├── docker-compose.yml    # Multi-container setup
├── Dockerfile            # Multi-stage production build
└── pyproject.toml        # Project config and dependencies
```
