# Features

Feature inventory for the User Registration API.

| Feature | Status | Layer | Key Files |
|---------|--------|-------|-----------|
| Health check endpoint | Done | API | `main.py` |
| Structured logging + correlation IDs | Done | Core | `core/logging.py`, `api/middlewares/logging.py` |
| Custom exception handlers | Done | Core | `core/exceptions.py` |
| PostgreSQL database layer | Done | Infrastructure | `infrastructure/database/` |
| User registration (`POST /users`) | Done | API + Domain | `api/routers/users.py`, `domain/services.py` |
| Email verification (4-digit code) | Pending | Infrastructure | |
| Account activation (Basic Auth) | Pending | API + Domain | |
| Integration tests | Pending | Tests | |
| Architecture documentation | Done | Docs | `ARCHITECTURE.md` |
