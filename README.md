# IT Ticketing System

Internal IT ticketing platform. Milestone 2 delivers ticket creation, queues, workflow, comments, categories, and ticket history on top of the Milestone 1 identity/RBAC foundation.

## Current status

**Milestone 2 is implemented and tested:** tickets, assignment, centralized status workflow, public comments, internal notes (filtered in the API), status/assignment history, categories, and the employee/admin ticket UI.

Still later by design: attachments/MinIO usage, notifications worker, SLA timers, reports.

## Requirements

- Docker Desktop (recommended), or
- Python 3.12+, Node.js 20+, PostgreSQL 16, Redis 7

## Quick start (Docker)

```bash
copy .env.example .env
docker compose up --build
```

On first run, seed development users:

```bash
docker compose exec backend python -m app.database.seed
```

| Service | URL |
| --- | --- |
| Web UI | http://localhost:5173 |
| API | http://localhost:8000 |
| OpenAPI | http://localhost:8000/docs |
| PostgreSQL | localhost:5433 |
| Redis | localhost:6379 |
| MinIO console | http://localhost:9001 |

Development logins (from `.env.example` — never use in production):

| Role | Name | Email | Password |
| --- | --- | --- | --- |
| Admin | Hardik | hardik@example.com | ChangeMe!Admin123 |
| Admin | Ronald | ronald@example.com | ChangeMe!Admin123 |
| Admin | Sanjay | sanjay@example.com | ChangeMe!Admin123 |
| Employee | Jordan Lee | employee@example.com | ChangeMe!Employee123 |

## Local backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
alembic upgrade head
python -m app.database.seed
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

PostgreSQL and Redis must be running. `docker compose up postgres redis -d` is enough for local API work.

## Local frontend

```bash
cd frontend
copy .env.example .env
npm install
npm run dev
```

## Environment variables

See `.env.example`. Important groups: `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, token lifetimes, MinIO, CORS, and seed credentials.

Never commit `.env` or real secrets.

## Database migrations

```bash
cd backend
alembic upgrade head
alembic revision --autogenerate -m "describe the change"
```

Production schema changes go through Alembic only.

## Seed data

```bash
docker compose exec backend python -m app.database.seed
python scripts/seed.py
```

Seeds departments, IT teams, categories, tags, permission catalog, system roles, and the three development users.

## Testing

```bash
docker compose up postgres redis -d
cd backend
pytest -q
```

Or:

```bash
docker compose exec backend pytest -q
```

## Documentation

- `docs/architecture.md` — modules, APIs, RBAC matrix, workflow, Milestone 1 tasks, risks
- `docs/database.md` — schema, ER diagram, indexes, pooling
- `docs/authentication.md`
- `docs/rbac.md`
- `docs/ticket-workflow.md`
- `docs/sla.md`
- `docs/api.md`
- `docs/development.md`
