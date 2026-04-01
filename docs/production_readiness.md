# Production Readiness

Analysis of what is missing before this service can be deployed to production.

---

## Blockers (P0)

### 1. TLS / HTTPS

Basic Auth transmits `base64(email:password)` in every request header. Without TLS, credentials are trivially interceptable.

Current state: the app exposes port 8000 over plain HTTP. No TLS termination, no HSTS header.

Required:
- A reverse proxy (nginx, Traefik) handling TLS termination, or
- A FastAPI middleware that rejects non-HTTPS requests in production
- `Strict-Transport-Security` header on all responses

> **Note:** Basic Auth is a requirement from the [original specification](user_registration_api.md). In production, TLS termination at the reverse proxy layer is mandatory to secure credentials in transit.

---

### 2. Rate Limiting

No protection on `POST /users` or `POST /users/activation-code`.

Risks:
- `POST /users` runs `bcrypt` at 12 rounds (~250–500ms CPU) on every call → thread pool exhaustion / CPU DoS
- `POST /users/activation-code` can be used to flood a victim's inbox

Rate limiting is an infrastructure concern and must be handled at the reverse proxy / API gateway layer (nginx `limit_req`, Traefik `rateLimit` middleware, AWS API Gateway throttling, Cloudflare rate limiting, etc.). This keeps the application stateless and avoids introducing a shared-state dependency (Redis) for a concern that the proxy already handles with full visibility into real client IPs.

The application does not implement rate limiting directly.

> **Note:** if the target infrastructure already includes a reverse proxy or API gateway with built-in rate limiting, no additional action is required on the application side.

---

### 3. Secrets Management

`docker-compose.yml` does not set `APP_HMAC_SECRET`. The app startup guard raises `RuntimeError` when the default value is used with `debug=False` — the stack crashes on `docker compose up`.

Additional defaults that must never reach production:
- `database_url` defaults to `postgres:postgres@localhost`
- `email_api_key` defaults to empty string

Required: inject secrets via Docker Secrets, a secrets manager (Vault, AWS Secrets Manager), or CI/CD environment variables. No defaults should silently pass in a production environment.

> **Note:** depends on the target infrastructure. Ideally, secrets should be managed through a dedicated secret manager (Vault, AWS Secrets Manager, GCP Secret Manager) rather than plain environment variables.

---

### 4. Real Email Provider

`APP_EMAIL_MOCK=true` by default. The mock service logs but does not deliver emails.

Required for production:
- `APP_EMAIL_MOCK=false`
- `APP_EMAIL_API_URL` and `APP_EMAIL_API_KEY` pointing to a real provider (SendGrid, Mailgun, AWS SES, etc.)
- `APP_EMAIL_FROM` set to a domain with valid SPF/DKIM records

---

## Infrastructure Gaps (P1)

### 5. ~~Versioned Schema Migrations~~ ✅ Resolved

Implemented via yoyo-migrations with versioned SQL files in `infrastructure/database/migrations/`. Migration history is tracked in the `_yoyo_migration` table. Applied automatically on startup via `run_migrations()`.

---

### 6. ~~Health Check Does Not Cover the Email Service~~ ✅ Resolved

`GET /health` now checks both database and email service connectivity. Returns a structured response with component statuses:
- `{"status": "healthy", "components": {"database": "up", "email": "up"}}` — all services operational (200)
- `{"status": "degraded", "components": {"database": "up", "email": "down"}}` — email unreachable (200)
- `503` — database unreachable

---

### 7. ~~Graceful Shutdown~~ ✅ Resolved

Uvicorn is configured with `--timeout-graceful-shutdown 5` in both the `Dockerfile` and `Procfile`, allowing in-flight requests to complete before shutdown.

---

### 8. Worker Configuration

The `Dockerfile` and `docker-compose.yml` do not configure `--workers` or `--worker-connections`. A single uvicorn process with the default settings is not suitable for production load.

Options:
- Multiple uvicorn workers: `uvicorn app.main:app --workers 4`
- gunicorn + uvicorn worker class for process supervision
- Horizontal scaling via the container orchestrator (Kubernetes, ECS)

---

## Application Security Gaps (P2)

### 9. Email Enumeration via HTTP 409

`POST /users` returns `HTTP 409 Conflict` with `error_code: "USER_ALREADY_EXISTS"` when the email is already registered. Any unauthenticated caller can enumerate registered emails.

Fix: return `HTTP 202 Accepted` with a generic message regardless of whether the email exists:
> "If this email address is not already registered, an activation email has been sent."

`POST /users/activation-code` already implements this pattern correctly.

---

### 10. No Expiry for Unactivated Accounts

Accounts created but never activated remain in the database indefinitely. This allows unbounded accumulation of unverified records and can be exploited to reserve email addresses.

Fix: a scheduled cleanup job (or a DB-level TTL mechanism) to purge accounts that have remained inactive beyond a configurable threshold (e.g. 24 hours).

---

### 11. No Session Revocation

Basic Auth is stateless — there is no mechanism to invalidate a user's access (logout, forced revocation). This is a known limitation of the Basic Auth scheme required by the spec. It should be documented as a constraint for anyone operating the service.

---

## Observability Gaps (P3)

### 12. No Metrics Endpoint

No Prometheus or OpenTelemetry instrumentation. In production, the following should be tracked:
- Request latency per endpoint (p50, p95, p99)
- Error rates by status code
- Active database connections
- Failed activation attempts (brute-force signal)
- Email delivery failures

Fix: `prometheus-fastapi-instrumentator` or OpenTelemetry SDK with a Prometheus exporter.

---

### 13. Logs Not in Structured JSON Format

Logs are written to stdout (correct for containers), but the formatter outputs human-readable text. Log aggregation systems (Datadog, ELK, Loki) require JSON-structured logs for reliable parsing and querying.

Fix: replace the current formatter with a JSON formatter (e.g. `python-json-logger`). The correlation ID and log level are already present in the log record — only the output format needs to change.

---

### 14. No Alerting on Critical Events

The following events produce log lines but no alerts:
- Activation lockout triggered (brute-force attempt detected)
- Repeated email delivery failures
- Database unreachable (returns 503 on health check)
- Startup with insecure default secrets

Fix: integrate with an alerting system (PagerDuty, OpsGenie) or configure log-based alerts in the observability platform.

---

## Summary

| Priority | Gap | Effort |
|---|---|---|
| P0 | TLS / HTTPS termination | Infrastructure |
| P0 | Rate limiting (reverse proxy — nginx, Traefik, API Gateway) | Infrastructure |
| P0 | Secrets management — no defaults in production | Infrastructure |
| P0 | Real email provider configured | Configuration |
| ~~P1~~ | ~~Versioned schema migrations~~ | ✅ Done |
| ~~P1~~ | ~~Health check covers email service~~ | ✅ Done |
| P1 | Email enumeration — HTTP 409 → 202 | ~30 min |
| ~~P1~~ | ~~Graceful shutdown~~ | ✅ Done |
| P1 | Worker configuration (multi-process) | ~1h |
| P2 | Cleanup job for unactivated accounts | ~2h |
| P2 | Structured JSON logs | ~1h |
| P3 | Prometheus / OpenTelemetry metrics | ~1 day |
| P3 | Alerting on critical events | Infrastructure |

The application code is production-quality. The blocking gaps are primarily **infrastructure** (TLS, secrets, email provider) and **two code changes**: rate limiting and the email enumeration fix on `POST /users`. Everything else is incremental hardening.
