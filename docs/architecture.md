# Architecture

This document describes the architecture of the internal IT Ticketing System. It is the source of truth for Milestone 1 and the intended shape of later milestones.

The first runnable milestone is **authentication, RBAC, and organization structure**. Tickets, SLA, attachments, and dashboards are designed here and implemented later.

## 1. Goals

- Support a few hundred users now, and thousands of users plus millions of historical tickets later, without rewriting the core domain.
- Prefer a **modular monolith** over microservices.
- Keep module boundaries explicit so a module can be extracted into a service later if operational need appears.
- Do not over-engineer V1: no Kafka, Kubernetes, Elasticsearch, or extra services.

## 2. High-level shape

```text
Browser (React SPA)
        │
        ▼
FastAPI API  (/api/v1)
        │
        ├── PostgreSQL   (system of record)
        ├── Redis        (cache, rate limits, future queues)
        └── MinIO        (attachments from Milestone 3)
                │
                ▼
        Background workers (Milestone 3+)
```

The API is **stateless**. Access tokens are JWTs. Refresh-token revocation and rate-limit counters live in PostgreSQL and Redis, not in process memory. Multiple API instances can run behind a load balancer.

## 3. Modular monolith

Each backend module owns its models, schemas, repository, service, and router. HTTP handlers do not contain business rules. The call path is:

```text
Router → Service → Repository → Database
```

Cross-module side effects (audit, notifications, SLA) go through an **in-process domain event bus** after the originating transaction commits. Modules must not import each other's routers or reach into another module's repository.

### 3.1 Module responsibilities

| Module | Responsibility | Milestone |
| --- | --- | --- |
| `config` | Typed settings from environment variables | 1 |
| `database` | Engine, session, pool, base model, seed entrypoint | 1 |
| `common` | Errors, logging, middleware, events, mixins | 1 |
| `auth` | Login, JWT access tokens, refresh-token lifecycle, logout, RBAC dependency | 1 |
| `users` | User entity, profile, disable, department/manager links | 1 |
| `roles` | Roles, permissions, role-permission grants | 1 |
| `departments` | Organizational departments | 1 |
| `teams` | IT teams and membership | 1 |
| `audit` | Immutable audit log writer and read API | 1 (write), 6 (admin read) |
| `tickets` | Ticket aggregate, numbers, assignment, filters | 2 |
| `comments` | Public comments and internal notes | 2 |
| `workflows` | Centralized status-transition rules | 2 |
| `categories` | Hierarchical categories/subcategories | 2 |
| `attachments` | Object-storage metadata and upload policy | 3 |
| `notifications` | In-app notifications and email job enqueue | 3 |
| `integrations` | Future email-to-ticket, chat, SSO adapters | later |
| `sla` | Policies, timers, pause/resume, events | 4 |
| `reports` | Read-side operational metrics, isolated from ticket writes | 5 |
| `workflows` / automation | Configurable rules engine | later |

Future modules exist as packages with a documented purpose. They do not expose fake HTTP APIs.

## 4. Domain events

Events are typed, in-process messages. They are recorded during a unit of work and **published only after a successful commit**.

Initial event names (stable for later automation):

- `user.created`, `user.updated`, `user.disabled`, `role.changed`
- `ticket.created`, `ticket.updated`, `ticket.assigned`
- `ticket.status_changed`, `ticket.comment_added`
- `ticket.resolved`, `ticket.closed`, `ticket.reopened`
- `ticket.sla_warning`, `ticket.sla_breached`

V1 bus: Python callbacks registered at process start. The interface is swap-compatible with a Redis/queue publisher later. Kafka is not used.

Typical flow:

```text
Service mutates aggregates
        → session.flush()
        → enqueue DomainEvent on the session
        → commit
        → EventBus.publish
              → Audit handler
              → Notification handler (M3)
              → SLA handler (M4)
```

## 5. Initial API surface

Version prefix: `/api/v1`.

### 5.1 Milestone 1

| Method | Path | Auth | Permission |
| --- | --- | --- | --- |
| `GET` | `/health` | none | — |
| `GET` | `/ready` | none | — |
| `POST` | `/api/v1/auth/login` | none | — (rate limited) |
| `POST` | `/api/v1/auth/refresh` | refresh token | — |
| `POST` | `/api/v1/auth/logout` | refresh token | — |
| `GET` | `/api/v1/users/me` | access token | authenticated |
| `GET` | `/api/v1/users` | access token | `user.view` |
| `POST` | `/api/v1/users` | access token | `user.create` |
| `GET` | `/api/v1/users/{id}` | access token | self or `user.view` |
| `PATCH` | `/api/v1/users/{id}` | access token | `user.update` |
| `POST` | `/api/v1/users/{id}/disable` | access token | `user.disable` |
| `PUT` | `/api/v1/users/{id}/roles` | access token | `role.manage` |
| `GET` | `/api/v1/roles` | access token | `role.manage` or `user.view` |
| `GET` | `/api/v1/roles/{id}` | access token | `role.manage` |
| `POST` | `/api/v1/roles` | access token | `role.manage` |
| `PATCH` | `/api/v1/roles/{id}` | access token | `role.manage` |
| `PUT` | `/api/v1/roles/{id}/permissions` | access token | `role.manage` |
| `GET` | `/api/v1/permissions` | access token | `role.manage` |
| `GET` | `/api/v1/departments` | access token | authenticated |
| `POST` | `/api/v1/departments` | access token | `department.manage` |
| `GET` | `/api/v1/departments/{id}` | access token | authenticated |
| `PATCH` | `/api/v1/departments/{id}` | access token | `department.manage` |
| `GET` | `/api/v1/teams` | access token | authenticated |
| `POST` | `/api/v1/teams` | access token | `team.manage` |
| `GET` | `/api/v1/teams/{id}` | access token | authenticated |
| `PATCH` | `/api/v1/teams/{id}` | access token | `team.manage` |
| `POST` | `/api/v1/teams/{id}/members` | access token | `team.manage` |
| `DELETE` | `/api/v1/teams/{id}/members/{user_id}` | access token | `team.manage` |

### 5.2 Milestone 2

| Method | Path |
| --- | --- |
| `POST` | `/api/v1/tickets` |
| `GET` | `/api/v1/tickets` |
| `GET` | `/api/v1/tickets/{id}` |
| `PATCH` | `/api/v1/tickets/{id}` |
| `POST` | `/api/v1/tickets/{id}/assign` |
| `POST` | `/api/v1/tickets/{id}/status` |
| `POST` | `/api/v1/tickets/{id}/comments` |
| `POST` | `/api/v1/tickets/{id}/attachments` |
| `GET` | `/api/v1/tickets/{id}/history` |
| `GET` | `/api/v1/tickets/{id}/timeline` |

SQLAlchemy models are never returned from the API. Pydantic v2 schemas are the contract.

Error envelope:

```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "You do not have permission to perform this action."
  }
}
```

## 6. RBAC permission matrix

Authorization is **permission-based**, never hardcoded role names in services. Roles are bundles of permission codes stored in `roles`, `permissions`, `role_permissions`, and `user_roles`.

V1 has two roles: **Employee** and **Admin**. Admins (Hardik, Ronald, Sanjay) can view every ticket and assign it to one of themselves to resolve.

| Permission | Employee | Admin |
| --- | --- | --- |
| `ticket.create` | ✓ | ✓ |
| `ticket.view_own` | ✓ | ✓ |
| `ticket.view_all` | | ✓ |
| `ticket.update` | | ✓ |
| `ticket.assign` | | ✓ |
| `ticket.reassign` | | ✓ |
| `ticket.change_priority` | | ✓ |
| `ticket.comment` | ✓ | ✓ |
| `ticket.internal_note` | | ✓ |
| `ticket.resolve` | | ✓ |
| `ticket.close` | | ✓ |
| `ticket.reopen` | ✓ | ✓ |
| `user.view` / `user.create` / `user.update` / `user.disable` | | ✓ |
| `role.manage` / `team.manage` / `department.manage` / `category.manage` | | ✓ |
| `sla.manage` / `workflow.manage` / `report.view` / `audit.view` / `system.manage` | | ✓ |

Ticket permissions are seeded in Milestone 1 and enforced by ticket APIs.

A user may hold multiple roles. Effective permissions are the union of all granted codes. Permission checks load from PostgreSQL and may be cached briefly in Redis, keyed by user id.

## 7. Ticket lifecycle (designed, implemented in Milestone 2)

Statuses are enum-safe strings. Transition rules live only in the workflow service.

| From | Allowed to |
| --- | --- |
| `NEW` | `OPEN`, `ASSIGNED`, `CANCELLED`, `REJECTED` |
| `OPEN` | `ASSIGNED`, `IN_PROGRESS`, `CANCELLED`, `REJECTED` |
| `ASSIGNED` | `IN_PROGRESS`, `OPEN`, `CANCELLED` |
| `IN_PROGRESS` | `WAITING_FOR_USER`, `WAITING_FOR_VENDOR`, `ON_HOLD`, `RESOLVED` |
| `WAITING_FOR_USER` | `IN_PROGRESS`, `ON_HOLD`, `RESOLVED` |
| `WAITING_FOR_VENDOR` | `IN_PROGRESS`, `ON_HOLD` |
| `ON_HOLD` | `IN_PROGRESS` |
| `RESOLVED` | `CLOSED`, `REOPENED` |
| `REOPENED` | `ASSIGNED`, `IN_PROGRESS` |
| `CLOSED` | none (reopen is a later policy if enabled) |
| `CANCELLED` | none |
| `REJECTED` | none |

Invalid transitions return `409` with code `INVALID_STATUS_TRANSITION`. Every successful transition writes `ticket_status_history`. Assignment writes `ticket_assignments`.

This table is the V1 default workflow. The workflow module is designed so a later configuration table can replace the in-code matrix without changing ticket routes.

## 8. Milestone 1 implementation tasks

1. Repository layout, Docker Compose (PostgreSQL, Redis, MinIO, API, frontend), `.env.example`.
2. FastAPI app, pydantic-settings, structured logging, request id middleware.
3. SQLAlchemy 2 async engine with connection pooling, Alembic, first migration.
4. Health (`/health`) and readiness (`/ready` checks PostgreSQL and Redis).
5. Departments, teams, team members.
6. Users with Argon2 password hashes; no plaintext passwords.
7. Roles, permissions, role-permission and user-role mapping.
8. JWT access tokens (short-lived) and hashed refresh tokens with revocation and rotation.
9. Login, refresh, logout, `GET /users/me`.
10. Permission dependency on every protected mutating admin route.
11. Audit log writer for user and role changes.
12. Seed: departments, IT teams, roles, permissions, admin / agent / employee users.
13. Tests: auth, refresh/revoke, anonymous rejection, RBAC denial, department/role assignment.
14. SPA: login, current user, admin screens for users, roles, departments, and teams.

**Out of scope for Milestone 1:** tickets, comments, attachments, SLA, notifications worker, reports, dashboards beyond current-user home.

## 9. Scalability principles (V1 constraints)

- Stateless API processes; pool PostgreSQL connections (`pool_size=10`, `max_overflow=20`, `pool_pre_ping=true`, `pool_recycle=1800`). Production may later put PgBouncer in front; it is not required now.
- Redis for rate limits and future job queues. RQ is the planned worker (simplest Redis-backed option) from Milestone 3.
- Cursor or limit/offset pagination on every list; never return unbounded collections.
- Object storage for files; PostgreSQL stores metadata only.
- Indexes documented in `docs/database.md`. Composite indexes are added when a query pattern is real.

## 10. Architectural risks and later work

| Risk | Why it matters | Later mitigation |
| --- | --- | --- |
| Ticket number generation under concurrency | `IT-2026-000001` must be unique | Yearly sequence table or `SELECT … FOR UPDATE` on a counter row |
| SLA business hours | V1 uses elapsed minutes | Policy calendar, holidays, pause on `WAITING_FOR_USER` |
| Internal notes leakage | Employees must never see them | Filter in the comment service, not the UI |
| Full-text search at millions of tickets | `ILIKE` will degrade | PostgreSQL `tsvector` first, OpenSearch only if needed |
| Reporting vs OLTP | Heavy aggregates block ticket writes | Isolated reports module, later read replica / materialized views |
| SSO | Entra ID / LDAP likely in enterprises | Auth module already isolates password login; add OIDC provider later |
| Email-to-ticket | Inbound mail mapping | Integrations module + `source=EMAIL` already in the ticket model |
| Refresh-token theft | Stolen cookie/header reuse | Rotation + reuse detection revokes the user’s token family |
| Permission cache staleness | Redis cache of permission codes | Short TTL and explicit invalidation on role change |
| Soft delete | Accidental hard deletes destroy auditability | Tickets are retained; users use `is_active` |

## 11. Frontend (Milestone 1)

React + Vite + TypeScript + Tailwind + React Router + TanStack Query + React Hook Form + Zod.

Routes: `/login`, `/dashboard`, `/profile`, `/tickets`, `/tickets/new`, `/tickets/:id`, `/agent/my-queue`, `/agent/unassigned`, plus admin users/roles/departments/teams.
