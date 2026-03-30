# Implementation Plan — User Registration API

Each step corresponds to one commit. Order is incremental: each commit builds on the previous.
Documentation (ARCHITECTURE.md, FEATURES.md, README) is created early and updated with each commit.

---

## Commit 1 ✅ — Project Skeleton

> `feat: initial project skeleton with FastAPI, uv, and code quality tooling`

- FastAPI app with lifespan events and `/health` endpoint
- Hexagonal architecture (api/core/domain/infrastructure)
- uv + dependency-groups, pre-commit hooks (ruff, mypy)
- GitHub CI, Dockerfile multi-stage, docker-compose (app + PostgreSQL 17)
- README with instructions

---

## Commit 2 ✅ — Documentation & Structured Logging

> Documentation initiale + logging middleware avec correlation IDs.

### Documentation
- [x] Create `ARCHITECTURE.md` — hexagonal architecture diagram (Mermaid), layers, dependency flow
- [x] Create `FEATURES.md` — feature inventory with status (all pending at this stage)
- [x] Update README — link to ARCHITECTURE.md and FEATURES.md

### Structured Logging
- [x] Create `core/logging.py` — configure structured JSON logging with `logging.config.dictConfig`
- [x] Create logging middleware — log method, path, status code, duration for every request
- [x] Add correlation ID (`X-Correlation-ID`) generation per request, propagated in all logs and response headers
- [x] Configure logging in lifespan startup
- [x] Add tests for logging middleware (correlation ID in response headers)
- [x] Update FEATURES.md — mark logging as done

---

## Commit 3 — Custom Exception Handling

> Domain exceptions + custom exception handlers for structured error responses.

- [ ] Create `core/exceptions.py` — domain exception classes:
  - `UserAlreadyExistsError`
  - `UserNotFoundError`
  - `InvalidActivationCodeError`
  - `ActivationCodeExpiredError`
  - `EmailSendError`
- [ ] Register custom exception handlers in `main.py`:
  - Domain exceptions → structured JSON `{"detail": "...", "error_code": "..."}`
  - Override `RequestValidationError` → consistent format
  - Override `StarletteHTTPException` → consistent format
- [ ] Add tests for each exception handler (correct status code, response format)
- [ ] Update FEATURES.md — mark exception handling as done

---

## Commit 4 — Database Layer (PostgreSQL)

> PostgreSQL connection pool with asyncpg, schema migration, repository pattern.

- [ ] Create `infrastructure/database/client.py` — asyncpg pool management (init/close in lifespan)
- [ ] Startup: initialize pool, run test query (`SELECT 1`), log DB connection status (success or failure)
- [ ] Shutdown: wait for all active transactions to complete, close all pool connections, log shutdown confirmation
- [ ] Create `infrastructure/database/migrations.py` — SQL schema creation on startup:
  - `users` table: id (UUID), email (unique), password_hash, is_active, created_at
  - `activation_codes` table: id (UUID), user_id (FK), code (4 digits), expires_at, used_at
- [ ] Create `domain/models.py` — domain entities (User, ActivationCode) as dataclasses
- [ ] Create `domain/ports.py` — abstract repository interfaces (UserRepository, ActivationCodeRepository)
- [ ] Create `infrastructure/database/repositories.py` — asyncpg implementations (raw SQL, no ORM)
- [ ] Create DB dependency with `Depends(yield)` pattern
- [ ] Update `core/config.py` — add DB settings
- [ ] Add tests with test database (or dependency override)
- [ ] Update ARCHITECTURE.md — add database layer details
- [ ] Update FEATURES.md — mark database layer as done

---

## Commit 5 — User Registration Endpoint

> `POST /users` — create a user with email and password.

- [ ] Create `api/schemas/users.py` — Pydantic models:
  - `UserRegisterRequest(email: EmailStr, password: SecretStr)` with validation
  - `UserResponse(id, email, is_active, created_at)`
- [ ] Create `domain/services.py` — `UserService` with registration logic:
  - Hash password with bcrypt
  - Check email uniqueness
  - Persist user via repository
- [ ] Create `api/routers/users.py` — `APIRouter(prefix="/users", tags=["users"])`
  - `POST /users` → 201 + `UserResponse`
  - Raise `UserAlreadyExistsError` if duplicate email
- [ ] Create `api/dependencies.py` — service injection via `Depends()`
- [ ] Include router in `main.py`
- [ ] Add tests: successful registration, duplicate email, invalid email, weak password
- [ ] Update ARCHITECTURE.md — add request flow diagram for registration
- [ ] Update FEATURES.md — mark user registration as done
- [ ] Update README — add API endpoint documentation

---

## Commit 6 — Email Service (Third-Party)

> Send 4-digit verification code by email. SMTP treated as third-party HTTP API.

- [ ] Add `EmailService` abstract interface to `domain/ports.py`
- [ ] Create `infrastructure/email/client.py` — implementation:
  - Log the 4-digit code to console (as allowed by spec)
  - Structure as HTTP client call to third-party SMTP API (mockable)
- [ ] Startup: initialize email client, verify SMTP server connectivity, log status (reachable or unreachable)
- [ ] Shutdown: close email client connections, log shutdown confirmation
- [ ] Generate 4-digit activation code, store in DB with 1-minute expiry
- [ ] Create `POST /users/{user_id}/activation-code` endpoint:
  - Generate code, save to DB, send via email service
- [ ] Add tests with email service dependency override (mock)
- [ ] Update ARCHITECTURE.md — add email service as external dependency
- [ ] Update FEATURES.md — mark email verification as done

---

## Commit 7 — Account Activation Endpoint

> `POST /users/activate` with Basic Auth + 4-digit code.

- [ ] Create `core/security.py` — `HTTPBasic` dependency, credential verification
- [ ] Create `api/schemas/users.py` — `ActivationRequest(code: str)` with 4-digit validation
- [ ] Add activation logic to `UserService`:
  - Verify Basic Auth (email + password)
  - Validate code matches and not expired (1 minute TTL)
  - Mark user as active
  - Raise `InvalidActivationCodeError` or `ActivationCodeExpiredError`
- [ ] Create `POST /users/activate` in router with `dependencies=[Depends(http_basic)]`
- [ ] Add tests: successful activation, expired code, wrong code, wrong credentials
- [ ] Update FEATURES.md — mark account activation as done
- [ ] Update README — add activation endpoint documentation

---

## Commit 8 — Integration Tests & Docker Test Setup

> End-to-end tests covering the full registration flow.

- [ ] Create integration test: register → receive code → activate with Basic Auth
- [ ] Add `docker-compose.test.yml` for running tests with real PostgreSQL
- [ ] Update CI to run integration tests
- [ ] Update README — add integration test instructions

---

## Commit 9 — Final Documentation Review

> Final pass on all documentation, verify all spec requirements.

- [ ] Update `ARCHITECTURE.md` — final architecture diagram with all components
- [ ] Update `FEATURES.md` — verify all features marked as done
- [ ] Update README — final API documentation, all endpoints, complete instructions
- [ ] Verify all spec requirements are met:
  - [x] Create user with email and password
  - [x] Send 4-digit code by email
  - [x] Activate with Basic Auth + code
  - [x] 1-minute code expiry
  - [x] FastAPI: async/await, Depends, Pydantic, exception handlers, lifespan
  - [x] No ORM, raw SQL with asyncpg
  - [x] Docker + docker-compose
  - [x] Tests
  - [x] Architecture schema
