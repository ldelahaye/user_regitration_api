## FastAPI Best Practices

These practices MUST be followed in all code written for this project. They are derived from the official FastAPI documentation.

### Type Hints & Pydantic
- Use `Annotated` types for all dependency injection: `Annotated[Type, Depends(dep)]`
- Create reusable type aliases for common dependencies: `CurrentUser = Annotated[User, Depends(get_current_user)]`
- Separate request/response schemas (`api/schemas/`) from domain models (`domain/models.py`)
- Use Pydantic `BaseModel` for all API schemas with strict validation (`Field(min_length=, max_length=, etc.)`)
- Use `EmailStr` for email validation, `SecretStr` for passwords in schemas
- Set `response_model` and `status_code` on all path operations

### Dependency Injection
- Use `Depends()` for all cross-cutting concerns: DB connections, auth, services
- Dependencies can be async or sync — mix freely
- Use `yield` dependencies for resource lifecycle (DB pool acquire/release)
- Use decorator-level `dependencies=[Depends(...)]` for validation-only deps (no return needed)
- Use global `app = FastAPI(dependencies=[...])` for app-wide deps
- Override dependencies in tests with `app.dependency_overrides[dep] = mock_dep`

### Routers & Project Structure
- Use `APIRouter` per feature domain with `prefix=` and `tags=[]`
- Include routers in `main.py` via `app.include_router(router)`
- Place shared dependencies in `api/dependencies.py`
- Use relative imports within `app` package

### Error Handling
- `raise HTTPException(status_code=, detail=)` — never return errors
- Create custom domain exceptions in `core/exceptions.py` (e.g. `UserAlreadyExistsError`, `ActivationCodeExpiredError`, `InvalidActivationCodeError`)
- Register custom exception handlers with `@app.exception_handler(ExcClass)` to convert domain exceptions into structured HTTP responses
- Override `RequestValidationError` handler for consistent error format across all endpoints
- Always register handlers for `starlette.exceptions.HTTPException` (not just FastAPI's)
- Use structured error response format: `{"detail": "message", "error_code": "DOMAIN_ERROR_CODE"}`

### Security
- Use `HTTPBasic` from `fastapi.security` for Basic Auth (as required by spec for account activation)
- Never store plaintext passwords — use bcrypt hashing
- Use `secrets.compare_digest()` for timing-safe string comparison
- Return `WWW-Authenticate` header with 401 responses

### Lifespan & Resources
- Use `@asynccontextmanager` lifespan (not deprecated `on_event`)
- Initialize DB pool, email client in startup; close in shutdown
- Store shared resources in `app.state`

### Logging
- Use Python `logging` module — never `print()` (enforced by ruff T20)
- Use `logging.getLogger(__name__)` in each module
- Log at appropriate levels: ERROR for failures, WARNING for degraded, INFO for events
- Implement request logging middleware with correlation IDs

### Testing
- Use `httpx.AsyncClient` with `ASGITransport` for async tests
- Use `pytest-asyncio` with `asyncio_mode = "auto"`
- Override dependencies for isolation — never hit real external services in tests
- One test = one unique behavior

---

## Project Context

Before starting any task, read these files for full project context:

- [README.md](README.md) — Architecture, tech stack, services, communication flow, auth model
- [FEATURES.md](FEATURES.md) — Feature inventory with status, services involved, and key source files
- [ARCHITECTURE.md](ARCHITECTURE.md) — High-level architecture overview
- [tasks/todo.md](tasks/todo.md) — Current milestones and implementation plan
- [tasks/lessons.md](tasks/lessons.md) — Patterns learned from past corrections

---

## Workflow Orchestration

### 1. Plan Node Default
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately - don't keep pushing
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

### 2. Subagent Strategy
- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One task per subagent for focused execution

### 3. Self-Improvement Loop
- After ANY correction from the user: update `tasks/lessons.md` with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant project

### 4. Verification Before Done
- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

### 5. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes - don't over-engineer
- Challenge your own work before presenting it

### 6. Autonomous Bug Fixing
- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests - then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

## Task Management

1. **Plan First**: Write plan to `tasks/todo.md` with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review section to `tasks/todo.md`
6. **Capture Lessons**: Update `tasks/lessons.md` after corrections

## Core Principles

- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.
