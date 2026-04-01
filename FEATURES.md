# Features

Feature inventory for the User Registration API.

| Feature | Status | Layer | Key Files |
|---------|--------|-------|-----------|
| Health check endpoint | Done | API | `main.py` |
| Structured logging + correlation IDs | Done | Core | `core/logging.py`, `api/middlewares/logging.py` |
| Custom exception handlers | Done | Core | `core/exception_handlers.py`, `domain/exceptions.py` |
| PostgreSQL database layer | Done | Infrastructure | `infrastructure/database/` |
| User registration (`POST /users`) | Done | API + Domain | `api/routers/users.py`, `domain/services.py` |
| Email verification (auto-send on registration + re-request by email) | Done | Infrastructure | `infrastructure/email/client.py`, `domain/services.py` |
| Password policy validation (configurable) | Done | Domain | `domain/services.py`, `core/config.py` |
| HMAC-hashed activation codes | Done | Infrastructure | `infrastructure/database/repositories.py` |
| Brute-force protection (activation lockout) | Done | Domain + Infrastructure | `domain/services.py`, `infrastructure/database/repositories.py` |
| Account activation (Basic Auth) | Done | API + Domain | `api/routers/users.py`, `domain/services.py` |
| Current user info (`GET /users/me`) | Done | API | `api/routers/users.py`, `api/dependencies.py` |
| Integration tests | Done | Tests | `tests/integration/` |
| Versioned database migrations (yoyo) | Done | Infrastructure | `infrastructure/database/migrations/` |
| CI pipeline (lint, test, integration) | Done | CI/CD | `.github/workflows/ci.yml` |
| Security scanning (CodeQL + Grype) | Done | CI/CD | `.github/workflows/codeql.yml`, `.github/workflows/security.yml` |
| Dependency updates (Dependabot) | Done | CI/CD | `.github/dependabot.yml` |
| Container image build (Paketo + GHCR) | Done | CI/CD | `.github/workflows/ci.yml` |
| Test coverage reporting on PRs | Done | CI/CD | `.github/workflows/ci.yml` |
| Graceful shutdown (uvicorn) | Done | Infrastructure | `Dockerfile`, `Procfile` |
| Architecture documentation | Done | Docs | `ARCHITECTURE.md` |
