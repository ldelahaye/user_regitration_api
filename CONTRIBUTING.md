# Contributing to user-registration-api

Thank you for your interest in contributing. This document explains how to report issues, propose changes, and submit pull requests.

---

## Code of Conduct

Be respectful and constructive. Focus feedback on code, not people. Discriminatory or harassing behavior will not be tolerated.

---

## How to Report a Bug

Open an issue and include:

- A clear, descriptive title
- Steps to reproduce the problem
- Expected vs. actual behavior
- Relevant logs or error messages
- Environment details (Python version, OS, Docker version)

---

## How to Suggest a Feature

Open an issue with the `enhancement` label and describe:

- The problem you are trying to solve
- Your proposed solution and why it fits the existing architecture
- Alternatives you considered

Features are evaluated against the hexagonal architecture and existing design decisions documented in [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Development Setup

**Prerequisites:** Docker, [uv](https://github.com/astral-sh/uv) (for local development only)

```bash
# Install dependencies
uv sync

# Run unit tests
uv run pytest -m "not integration"

# Run integration tests (Docker only, no local Python needed)
docker compose -f docker-compose.test.yml run --rm app-test uv run pytest -m integration
docker compose -f docker-compose.test.yml down

# Lint and format
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# Type checking
uv run mypy
```

# Install and enable pre-commit hooks (run once after cloning)
uv run pre-commit install

Pre-commit hooks enforce `ruff` and `mypy` automatically on every commit.

---

## Branching Strategy

| Branch pattern     | Purpose                  |
|--------------------|--------------------------|
| `main`             | Production-ready, protected |
| `feat/<topic>`     | New features             |
| `fix/<topic>`      | Bug fixes                |

---

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add activation endpoint
fix: correct transaction rollback on email failure
docs: update ARCHITECTURE.md with email service section
test: add integration test for full registration flow
refactor: move _setup_db fixture to conftest
```

Include the sign-off trailer:

```
Signed-off-by: Your Name <your@email.com>
```

---

## Pull Requests

1. Branch off `main`
2. Keep the PR focused — one feature or fix per PR
3. All CI checks must pass (`lint` + `test` + `integration-test`)
4. Self-review against [CLAUDE.md](CLAUDE.md) before requesting review
5. Write or update tests for any changed behavior (one test = one unique behavior)
6. Update documentation if the change affects public-facing behavior or architecture

---

## Code Standards

This project follows hexagonal architecture (ports and adapters). Before contributing:

- Read [ARCHITECTURE.md](ARCHITECTURE.md) for the overall design
- Read [FEATURES.md](FEATURES.md) for the current feature inventory
- Domain logic lives in `src/app/domain/` — keep it free of infrastructure concerns
- Raw SQL via `asyncpg` — no ORM
- All API schemas use Pydantic with strict validation
- No `print()` — use `logging.getLogger(__name__)`
- Imports at module top level only — no local/inline imports

---

## AI-Assisted Development

This project was built with [Claude Code](https://claude.com/claude-code) as an AI pair programmer. Contributions generated with AI assistance are welcome, provided the contributor reviews, understands, and takes ownership of every change before submitting.
