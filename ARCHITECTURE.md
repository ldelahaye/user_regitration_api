# Architecture

## Overview

This project follows **hexagonal architecture** (ports & adapters) to separate business logic from infrastructure concerns.

## Layers

```mermaid
graph TD
    Client[HTTP Client] -->|HTTP Request| API

    subgraph Application
        API[API Layer<br/>Routers, Schemas, Dependencies]
        API -->|calls| Domain[Domain Layer<br/>Services, Models, Ports]
        Infra[Infrastructure Layer<br/>Repositories, Email Client] -->|implements| Domain
    end

    subgraph Core
        Config[Configuration]
        Logging[Structured Logging]
        Exceptions[Exception Handlers]
    end

    Infra -->|asyncpg| DB[(PostgreSQL)]
    Infra -->|HTTP API| SMTP[SMTP Service<br/>Third-Party]

    API -.->|uses| Core
    Domain -.->|uses| Core
    Infra -.->|uses| Core
```

### API Layer (`src/app/api/`)
- **Inbound adapters**: FastAPI routers, Pydantic request/response schemas
- Handles HTTP concerns: validation, serialization, status codes
- Delegates business logic to domain services via dependency injection

### Domain Layer (`src/app/domain/`)
- **Business rules**: registration, activation, code generation
- **Port interfaces**: abstract classes defining repository and service contracts
- **Models**: domain entities (User, ActivationCode)
- No dependency on infrastructure or framework

### Infrastructure Layer (`src/app/infrastructure/`)
- **Outbound adapters**: concrete implementations of domain ports
- Database repositories (asyncpg, raw SQL — no ORM)
- Email client (third-party SMTP service via HTTP API)

### Core (`src/app/core/`)
- Cross-cutting concerns shared across all layers
- Configuration (Pydantic Settings)
- Structured logging with correlation IDs
- Domain exception definitions and HTTP exception handlers

## Dependency Flow

```
API → Domain ← Infrastructure
```

Dependencies flow **inward**: the API layer and infrastructure layer depend on the domain layer, never the reverse. The domain layer defines port interfaces that infrastructure implements.

## Request Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant M as Middleware
    participant R as Router
    participant S as Service
    participant DB as PostgreSQL

    C->>M: HTTP Request
    M->>M: Generate Correlation ID
    M->>R: Forward Request
    R->>R: Validate (Pydantic)
    R->>S: Call Service
    S->>DB: Query/Insert
    DB-->>S: Result
    S-->>R: Domain Model
    R-->>M: HTTP Response
    M->>M: Log request (method, path, status, duration)
    M-->>C: Response + X-Correlation-ID
```

## External Services

| Service | Role | Connection |
|---------|------|------------|
| PostgreSQL 17 | User and activation code storage | asyncpg connection pool |
| SMTP (third-party) | Send verification emails | HTTP API call |
