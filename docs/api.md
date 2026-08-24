# API

Base URL: `/api/v1`. JSON request and response bodies. Pydantic v2 schemas only — ORM models are not serialized directly.

## Errors

All handled application errors use:

```json
{
  "error": {
    "code": "STRING_CODE",
    "message": "Human readable explanation."
  }
}
```

| HTTP | Typical codes |
| --- | --- |
| 400 | `VALIDATION_ERROR`, `INVALID_REQUEST` |
| 401 | `UNAUTHORIZED`, `INVALID_CREDENTIALS`, `INVALID_REFRESH_TOKEN`, `ACCOUNT_DISABLED` |
| 403 | `FORBIDDEN` |
| 404 | `NOT_FOUND` |
| 409 | `CONFLICT`, `INVALID_STATUS_TRANSITION`, `CONCURRENT_UPDATE` |
| 413 | `PAYLOAD_TOO_LARGE` |
| 422 | FastAPI/Pydantic validation (normalized to the envelope where possible) |
| 429 | `RATE_LIMITED` |

## Auth

### `POST /auth/login`

Request: `{ "email": "hardik@example.com", "password": "..." }`

Response `200`:

```json
{
  "access_token": "<jwt>",
  "refresh_token": "<opaque>",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": "uuid",
        "email": "hardik@example.com",
    "full_name": "Hardik",
    "is_active": true,
    "roles": ["Admin"],
    "permissions": ["user.view", "user.create"]
  }
}
```

### `POST /auth/refresh`

Request: `{ "refresh_token": "..." }` — same token response shape as login (user may be omitted or included).

### `POST /auth/logout`

Request: `{ "refresh_token": "..." }` — `204` empty body.

## Users

`GET /users/me` — `UserMe` including department, roles, permissions, team memberships.

List: `GET /users?limit=50&offset=0&q=&department_id=&is_active=`

Create: `POST /users` — email, password, full_name, optional employee_code, username, department_id, manager_id, role_ids.

## Roles and permissions

`GET /permissions` — catalog of codes.

`PUT /roles/{id}/permissions` — replace the set of permission ids for a non-conflicting custom or system role (system roles may be updated only by Admin in practice; V1 allows `role.manage`).

`PUT /users/{id}/roles` — replace role ids for a user.

## Departments and teams

Standard list/create/get/patch. Team members: `POST /teams/{id}/members` with `{ "user_id", "is_lead" }`.

## Pagination

Limit/offset for Milestone 1 lists. Default limit 50, max 100. Response:

```json
{
  "items": [],
  "total": 0,
  "limit": 50,
  "offset": 0
}
```

Ticket lists in Milestone 2 keep the same envelope; cursor pagination can be added for hot agent queues without breaking this shape if a `next_cursor` field is added later.

## Tickets

`POST /tickets` — create (`ticket.create`). Requester is the current user. Optional category, subcategory, priority, severity, tags.

`GET /tickets` — list with visibility rules (`view_own` / `view_team` / `view_all`). Query: `status`, `priority`, `requester_id`, `assigned_agent_id`, `assigned_team_id`, `department_id`, `category_id`, `ticket_number`, `q`, `date_from`, `date_to`, `unassigned`, `sort` (`created_at|updated_at|due_at|priority`), `order`, `limit`, `offset`.

`GET /tickets/{id}` — detail. Employees receive `403` for tickets they do not own.

`PATCH /tickets/{id}` — update fields (`ticket.update`). Optional `version` for optimistic concurrency (`409 CONCURRENT_UPDATE`).

`POST /tickets/{id}/assign` — `{ team_id, agent_id, version }`. Assigning from `NEW`/`OPEN`/`REOPENED` moves the ticket to `ASSIGNED`.

`POST /tickets/{id}/status` — `{ status, reason, resolution_summary, version }`. Invalid moves return `409 INVALID_STATUS_TRANSITION`. Resolving requires a summary.

`POST /tickets/{id}/comments` — `{ body, type: PUBLIC_COMMENT|INTERNAL_NOTE }`. Internal notes require `ticket.internal_note` and are omitted from employee reads.

`GET /tickets/{id}/comments`

`GET /tickets/{id}/history` — status history and assignment history.

`GET /tickets/{id}/timeline` — merged conversation for the detail page (internal notes filtered server-side).

`GET /categories` — hierarchical categories for ticket forms. `POST`/`PATCH` require `category.manage`.

## Health

- `GET /health` — process up: `{ "status": "ok" }`
- `GET /ready` — PostgreSQL `SELECT 1` and Redis `PING`: `{ "status": "ready", "checks": { "postgres": "ok", "redis": "ok" } }` or `503`

## Auth header

```text
Authorization: Bearer <access_token>
```
