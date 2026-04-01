# Library Choices

This document explains the rationale behind each dependency used in the project.
The spec states: *"You can use libraries for specific utilities: db connection pooling (asyncpg, psycopg), testing (pytest), validation (pydantic), etc."*

## Production Dependencies

### FastAPI (`fastapi[standard]`)

Required by the spec. The `[standard]` extra bundles uvicorn, email-validator, and other utilities needed for a production-ready setup.

Key features used:
- `Depends()` with `Annotated` types for dependency injection
- `yield` dependencies for transactional connection lifecycle
- `@asynccontextmanager` lifespan (startup/shutdown)
- Global exception handlers for structured error responses
- `APIRouter` for feature-based route organization

### Uvicorn (`uvicorn[standard]`)

ASGI server for running the FastAPI application. The `[standard]` extra includes `uvloop` (faster event loop on Linux) and `httptools` (faster HTTP parsing). This is the recommended server in the FastAPI documentation.

### asyncpg

Native async PostgreSQL driver using the binary protocol. Chosen over psycopg for this project because:

| Criteria | asyncpg | psycopg3 (async) |
|---|---|---|
| Architecture | Async-native from the ground up | Sync driver with async layer added in v3 |
| Protocol | PostgreSQL binary protocol | Text protocol by default (binary optional) |
| Performance | ~3-5x faster in benchmarks | Slower, but sufficient for most workloads |
| API surface | Minimal (`fetchrow`, `execute`, `fetch`) | Richer (server-side cursors, `COPY`, pipelines) |
| Async maturity | 10+ years, designed for asyncio | Stable async since psycopg 3.1 (2022) |
| Connection pooling | Built-in `asyncpg.create_pool()` | Separate `ConnectionPool` class |

**asyncpg wins here** because the project writes raw SQL (no ORM), needs only basic queries, and benefits from maximum async performance. psycopg3 would be the better choice if the project needed advanced features like `COPY`, `LISTEN/NOTIFY`, or a single driver for both sync and async code paths.

### Pydantic (`pydantic`, `pydantic-settings`)

- `pydantic`: Request/response validation via `BaseModel` schemas. Provides `EmailStr` for email validation, `SecretStr` for password fields, and `Field()` constraints (min/max length, regex patterns).
- `pydantic-settings`: Environment-based configuration with `BaseSettings`. Reads from `.env` files and environment variables with the `APP_` prefix, with type coercion and `SecretStr` support for sensitive values.

Both are part of the FastAPI ecosystem and required by the spec (*"validation (pydantic)"*).

### bcrypt

Industry-standard password hashing with configurable cost factor. bcrypt is specifically designed to be slow (cost factor 12 = ~250ms per hash), making brute-force attacks impractical.

Implementation note: bcrypt operations are CPU-bound and would block the async event loop. The project uses `asyncio.to_thread()` to offload hashing to the thread pool. This works because the bcrypt C extension releases the GIL during computation, allowing true parallel execution with the event loop.

### httpx

Async HTTP client used by `HttpEmailService` to call the email API. Chosen because:
- Natively async (`AsyncClient`) — no thread pool wrapper needed
- Same API as `requests` (familiar)
- Also used as the test client via `httpx.AsyncClient` + `ASGITransport` for testing FastAPI apps (recommended by FastAPI docs over the deprecated `TestClient` for async tests)

## Development Dependencies

### pytest + pytest-asyncio

Test framework. `pytest-asyncio` with `asyncio_mode = "auto"` allows writing `async def test_*` functions without decorators. Tests use `httpx.AsyncClient` with `ASGITransport` for HTTP-level testing and `AsyncMock` for service isolation.

### ruff

Linter and formatter replacing flake8, isort, black, and pyupgrade in a single tool. Configured with security rules (bandit via `S`), bug detection (bugbear via `B`), and `print()` prevention (`T20`). Runs as a pre-commit hook.

### mypy

Static type checker in `strict` mode. Catches type errors, missing return types, and incorrect annotations at development time. Runs as a pre-commit hook alongside ruff.

### pre-commit

Git hook manager that runs ruff (lint + format) and mypy before every commit. Prevents code quality regressions from reaching the repository.

## Libraries Not Used (and why)

| Library | Why not |
|---|---|
| **SQLAlchemy / Tortoise ORM** | Explicitly forbidden by the spec: *"No ORMs allowed"* |
| **psycopg3** | asyncpg is faster and better suited for this async-only, raw-SQL project (see comparison above) |
| **passlib** | Deprecated; `bcrypt` is used directly with the modern `hashpw`/`checkpw` API |
| **python-jose / PyJWT** | The spec requires Basic Auth for activation, not JWT. No token-based auth needed |
| **celery / arq** | Email sending is synchronous within the request. A task queue would be appropriate at scale but adds infrastructure complexity beyond the spec |
| **alembic** | Migrations are handled via raw SQL in `infrastructure/database/migrations.py` — consistent with the no-ORM constraint |
| **slowapi** | Rate limiting is identified as a future improvement but not required by the spec |
