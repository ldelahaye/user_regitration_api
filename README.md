# User Registration API

User registration API with email verification, built with FastAPI and PostgreSQL.

## Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Hexagonal architecture, layer diagram, data flow |
| [FEATURES.md](FEATURES.md) | Feature inventory with status and key files |

## Tech Stack

- **Language**: Python 3.13
- **Framework**: FastAPI
- **Database**: PostgreSQL 17 (raw SQL with asyncpg, no ORM)
- **Package Manager**: uv
- **Containerization**: Docker + docker-compose

## Quick Start

### Prerequisites

- Docker
- docker-compose

No local Python installation required.

### Run with Docker Compose

```bash
docker compose up --build
```

| Resource | URL |
|----------|-----|
| API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| Health check | http://localhost:8000/health |

### Stop

```bash
docker compose down
```

To also remove the database volume:

```bash
docker compose down -v
```

## Environment Variables

All variables use the `APP_` prefix and can be set in a `.env` file or passed to `docker compose`.

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_DEBUG` | `false` | Enable debug mode |
| `APP_DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/registration` | PostgreSQL connection URL |
| `APP_DATABASE_MIN_POOL_SIZE` | `2` | Minimum DB connection pool size |
| `APP_DATABASE_MAX_POOL_SIZE` | `10` | Maximum DB connection pool size |
| `APP_EMAIL_MOCK` | `true` | When `true`, emails are logged instead of sent |
| `APP_EMAIL_API_URL` | `http://localhost:8025/api/v1/send` | Email service API endpoint |
| `APP_EMAIL_API_KEY` | _(empty)_ | Email service API key |
| `APP_EMAIL_FROM` | `noreply@registration.local` | Sender address for outgoing emails |
| `APP_ACTIVATION_CODE_TTL_MINUTES` | `1` | Activation code validity duration (minutes) |
| `APP_ACTIVATION_MAX_ATTEMPTS` | `5` | Max failed activation attempts before lockout |
| `APP_BCRYPT_ROUNDS` | `12` | bcrypt cost factor |
| `APP_HMAC_SECRET` | _(must be set)_ | Server-side secret for HMAC-hashed activation codes |
| `APP_PASSWORD_MIN_LENGTH` | `12` | Minimum password length |
| `APP_PASSWORD_MAX_LENGTH` | `128` | Maximum password length |
| `APP_PASSWORD_REQUIRE_UPPERCASE` | `true` | Require at least one uppercase letter |
| `APP_PASSWORD_REQUIRE_LOWERCASE` | `true` | Require at least one lowercase letter |
| `APP_PASSWORD_REQUIRE_DIGIT` | `true` | Require at least one digit |
| `APP_PASSWORD_REQUIRE_SPECIAL` | `true` | Require at least one special character |

**Example `.env`:**
```env
APP_EMAIL_MOCK=false
APP_EMAIL_API_KEY=your-api-key
APP_EMAIL_FROM=noreply@yourdomain.com
APP_ACTIVATION_CODE_TTL_MINUTES=10
APP_HMAC_SECRET=your-random-secret-here
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
```

## Tests

### Unit tests

```bash
uv run pytest
```

### Integration tests

Integration tests require a real PostgreSQL instance.

```bash
# Start test database
docker compose -f docker-compose.test.yml up -d

# Run integration tests
uv run pytest -m integration

# Tear down
docker compose -f docker-compose.test.yml down
```

Or with a custom database URL:

```bash
TEST_DATABASE_URL=postgresql://user:pass@host:5432/dbname uv run pytest -m integration
```

### Code Quality

```bash
uv run ruff check src/ tests/    # Linting
uv run ruff format --check src/ tests/  # Formatting
uv run mypy                      # Type checking
```

## API Endpoints

| Method | Path | Auth | Description | Status Code |
|--------|------|------|-------------|-------------|
| `GET` | `/health` | — | Health check | 200 |
| `POST` | `/users` | — | Register a new user (auto-sends activation code) | 201 |
| `POST` | `/users/activation-code` | — | Re-request activation code by email | 201 |
| `POST` | `/users/activate` | Basic Auth | Activate account with 4-digit code | 200 |
| `GET` | `/users/me` | Basic Auth | Get current user info (active accounts only) | 200 |

### `POST /users`

Register a new user. An activation code is automatically sent by email.

**Request body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
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

If the email service is unavailable, the user is still created. A new code can be requested via `POST /users/activation-code`.

**Password policy:** minimum 12 characters, must include uppercase, lowercase, digit, and special character. These defaults follow [ANSSI R22](https://cyber.gouv.fr/publications/recommandations-relatives-lauthentification-multifacteur-et-aux-mots-de-passe) (guide "Multi-factor authentication and passwords", v2 — October 2021) which recommends a minimum entropy of 80 bits for user-chosen passwords without rate limiting, corresponding to 12+ characters with 4 character classes. All rules are configurable via environment variables.

**Errors:**
- `409` — Email already registered (`USER_ALREADY_EXISTS`)
- `422` — Weak password (`WEAK_PASSWORD`) or validation error (invalid email, unsupported lang)

### `POST /users/activation-code`

Re-request a 4-digit activation code by email. Always returns 201 regardless of whether the email exists (prevents user enumeration).

**Request body:**
```json
{
  "email": "user@example.com"
}
```

**Response (201):**
```json
{
  "detail": "If the email exists, an activation code has been sent"
}
```

### `POST /users/activate`

Activate a user account using HTTP Basic Auth and a 4-digit code.

**Authentication:** HTTP Basic Auth — email as username, password as password.

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
- `401` — Invalid credentials
- `422` — Validation error (code must be exactly 4 digits)
- `429` — Too many failed attempts (`ACTIVATION_CODE_LOCKED`)

### `GET /users/me`

Get the current authenticated user's information. Requires an active account.

**Authentication:** HTTP Basic Auth — email as username, password as password.

**Response (200):**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "is_active": true,
  "lang": "fr",
  "created_at": "2026-03-30T12:00:00Z"
}
```

**Errors:**
- `401` — Missing or invalid credentials
- `403` — Account not yet activated (`INACTIVE_USER`)

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
