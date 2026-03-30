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

## Commit 3 ✅ — Custom Exception Handling

> Domain exceptions + custom exception handlers for structured error responses.

- [x] Create `core/exceptions.py` — domain exception classes:
  - `UserAlreadyExistsError`
  - `UserNotFoundError`
  - `InvalidActivationCodeError`
  - `ActivationCodeExpiredError`
  - `EmailSendError`
- [x] Register custom exception handlers in `main.py`:
  - Domain exceptions → structured JSON `{"detail": "...", "error_code": "..."}`
  - Override `RequestValidationError` → consistent format
  - Override `StarletteHTTPException` → consistent format
- [x] Add tests for each exception handler (correct status code, response format)
- [x] Update FEATURES.md — mark exception handling as done

---

## Commit 4 ✅ — Database Layer (PostgreSQL)

> PostgreSQL connection pool with asyncpg, schema migration, repository pattern.

- [x] Create `infrastructure/database/client.py` — asyncpg pool management (init/close in lifespan)
- [x] Startup: initialize pool, run test query (`SELECT 1`), log DB connection status
- [x] Shutdown: close all pool connections, log shutdown confirmation
- [x] Create `infrastructure/database/migrations.py` — SQL schema creation on startup:
  - `users` table: id (UUID), email (unique), password_hash, is_active, lang, created_at
  - `activation_codes` table: id (UUID), user_id (FK), code (4 digits), expires_at, used_at
- [x] Create `domain/models.py` — domain entities (User, ActivationCode) as dataclasses
- [x] Create `domain/ports.py` — abstract repository interfaces (UserRepository, ActivationCodeRepository)
- [x] Create `infrastructure/database/repositories.py` — asyncpg implementations (raw SQL, no ORM)
- [x] Create DB dependency with `Depends(yield)` pattern + transaction commit/rollback
- [x] Pool stored in `app.state`, single connection per request shared across repositories
- [x] Update `core/config.py` — add DB settings (pool size)
- [x] Add integration tests with real PostgreSQL
- [x] Update ARCHITECTURE.md — add database layer details
- [x] Update FEATURES.md — mark database layer as done

---

## Commit 5 ✅ — User Registration Endpoint

> `POST /users` — create a user with email and password.

- [x] Create `api/schemas/users.py` — Pydantic models:
  - `UserRegisterRequest(email: EmailStr, password: SecretStr, lang: str)` with validation
  - `UserResponse(id, email, is_active, lang, created_at)`
- [x] Create `domain/services.py` — `UserService` with registration logic:
  - Hash password with bcrypt
  - Check email uniqueness
  - Persist user via repository
- [x] Create `api/routers/users.py` — `APIRouter(prefix="/users", tags=["users"])`
  - `POST /users` → 201 + `UserResponse`
  - Raise `UserAlreadyExistsError` if duplicate email
- [x] Create `api/dependencies.py` — service injection via `Depends()`
- [x] Include router in `main.py`
- [x] Add tests: successful registration, duplicate email, invalid email, weak password, invalid lang
- [x] Update FEATURES.md — mark user registration as done
- [x] Update README — add API endpoint documentation

---

## Commit 6 ✅ — Email Service (Third-Party)

> Send 4-digit verification code by email. SMTP treated as third-party HTTP API.

- [x] Add `EmailService` abstract interface to `domain/ports.py` (`check_connectivity`, `send_activation_code`, `close`)
- [x] Create `infrastructure/email/client.py` — two implementations:
  - `HttpEmailService`: real HTTP client (`httpx.AsyncClient`) calling SMTP API with Bearer auth
  - `ConsoleEmailService`: logs activation codes to console (when `APP_EMAIL_MOCK=true`)
  - `create_email_service()` factory selects implementation based on config
- [x] Config: `APP_EMAIL_MOCK`, `APP_EMAIL_API_URL`, `APP_EMAIL_API_KEY`, `APP_EMAIL_FROM`, `APP_ACTIVATION_CODE_TTL_MINUTES`
- [x] Startup: create email service via factory, verify SMTP connectivity (`HEAD` request, log reachable/unreachable), load templates
- [x] Shutdown: close email client connections, log shutdown confirmation
- [x] Generate 4-digit activation code (`secrets.randbelow`), store in DB with configurable TTL (default 1 min)
- [x] Create `POST /users/{user_id}/activation-code` endpoint (UUID path param validated by FastAPI)
- [x] Transactional safety: code persisted first, if email fails → transaction rollback (FastAPI yield dependency)
- [x] `get_active_code` SQL filters `expires_at > now()` — expired codes are rejected
- [x] `HttpEmailService` converts `httpx.HTTPError` → `EmailSendError` (502)
- [x] Multilingual email templates (fr, en, es, it, de) loaded from `.txt` files at startup
- [x] `User.lang` field added across full stack (model, migration, repo, schema, service)
- [x] Add tests: activation code send (201, 404), invalid lang (422)
- [x] Add integration tests: rollback on email failure, commit on success (real PostgreSQL)
- [x] Update ARCHITECTURE.md — email service section, transaction flow diagram, lang in schema
- [x] Update FEATURES.md — mark email verification as done

---

## Commit 7 ✅ — Account Activation Endpoint

> `POST /users/activate` with Basic Auth + 4-digit code.

- [x] Create `core/security.py` — `HTTPBasic` dependency, credential verification with `bcrypt.checkpw`
  - Dummy hash (`_DUMMY_HASH`) to prevent timing-based user enumeration
  - 401 response with `WWW-Authenticate: Basic` header
- [x] Create `api/schemas/users.py` — `ActivationRequest(code: str)` with 4-digit regex validation
- [x] Create `ActivationResponse` schema for typed `response_model`
- [x] Add `get_expired_code` port + repo method to distinguish expired from invalid codes
- [x] Add activation logic to `UserService.activate_user`:
  - Check user not already active
  - Validate code matches and not expired (SQL `expires_at > now()`)
  - If code not found, check if expired → `ActivationCodeExpiredError` vs `InvalidActivationCodeError`
  - Mark code as used, activate user
- [x] Create `POST /users/activate` in router with `get_authenticated_user` dependency
- [x] Single DB connection per request (FastAPI `use_cache=True` deduplication verified)
- [x] Add tests: successful activation (200), expired code (400), wrong code (400), invalid format (422), no credentials (401 + `WWW-Authenticate` header)
- [x] Update FEATURES.md — mark account activation as done
- [x] Update README — add activation endpoint documentation
- [x] Fix async-safe correlation ID logging: `contextvars.ContextVar` + single `CorrelationIdFilter` at startup (replaces per-request addFilter/removeFilter on root logger)

---

## Commit 8 — Integration Tests & Docker Test Setup

> End-to-end tests covering the full registration flow.

- [ ] Create integration test: register → receive code → activate with Basic Auth
- [ ] Add `docker-compose.test.yml` for running tests with real PostgreSQL
- [ ] Update CI to run integration tests
- [ ] Update README — add integration test instructions

---

## Commit 9 ✅ — Final Documentation Review

> Final pass on all documentation, verify all spec requirements.

- [x] Update `ARCHITECTURE.md` — final architecture diagram with all components
- [x] Update `FEATURES.md` — verify all features marked as done
- [x] Update README — final API documentation, all endpoints, complete instructions
- [x] Verify all spec requirements are met:
  - [x] Create user with email and password
  - [x] Send 4-digit code by email
  - [x] Activate with Basic Auth + code
  - [x] 1-minute code expiry
  - [x] FastAPI: async/await, Depends, Pydantic, exception handlers, lifespan
  - [x] No ORM, raw SQL with asyncpg
  - [x] Docker + docker-compose
  - [x] Tests (unit + integration)
  - [x] Architecture schema
