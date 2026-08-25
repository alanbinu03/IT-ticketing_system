# Development

## Requirements

- Docker and Docker Compose (recommended)
- Or locally: Python 3.12+, Node.js 20+, PostgreSQL 16, Redis 7

## Environment

Copy `.env.example` to `.env` and adjust if needed. Never commit `.env`.

Frontend uses `frontend/.env.example` → `frontend/.env`. Leave `VITE_API_URL` empty so Vite proxies `/api` to the backend (`http://127.0.0.1:8000`). Set `VITE_API_URL` only when the UI is hosted separately from the API.

## Docker (all services)

From the repository root:

```bash
docker compose up --build
```

Services:

| Service | URL |
| --- | --- |
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |
| PostgreSQL | localhost:5433 |
| Redis | localhost:6379 |
| MinIO API | http://localhost:9000 |
| MinIO console | http://localhost:9001 |
| Mailer (Nodemailer SMTP) | http://localhost:3010/health |

On first backend start the container runs `alembic upgrade head`. Seed separately:

```bash
docker compose exec backend python -m app.database.seed
```

Default development logins (from `.env.example`):

| Role | Name | Email | Password |
| --- | --- | --- | --- |
| Admin | Hardik | hardik@example.com | ChangeMe!Admin123 |
| Admin | Ronald | ronald@example.com | ChangeMe!Admin123 |
| Admin | Sanjay | sanjay@example.com | ChangeMe!Admin123 |
| Employee | Jordan Lee | employee@example.com | ChangeMe!Employee123 |

## Backend locally

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# Unix: source .venv/bin/activate
pip install -e ".[dev]"
# start postgres + redis (e.g. docker compose up postgres redis -d)
alembic upgrade head
python -m app.database.seed
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Frontend locally

```bash
cd frontend
npm install
npm run dev
```

## Mailer locally (Nodemailer)

OTP and ticket emails are sent by the Node mailer, not Python `smtplib`. With `SMTP_HOST` set, start it next to the API:

```bash
cd mailer
npm install
npm start
```

Confirm SMTP credentials with `npm run verify`. The API posts to `MAILER_URL` (default `http://127.0.0.1:3010`).

## Tests

PostgreSQL and Redis must be reachable (`DATABASE_URL`, `REDIS_URL`).

```bash
cd backend
pytest -q
```

The test suite uses a dedicated database name `ticketing_test` when `TEST_DATABASE_URL` is set; otherwise it uses `DATABASE_URL` (do not point this at a database you care about).

```bash
docker compose exec backend pytest -q
```

## Migrations

```bash
cd backend
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

Never rely on `create_all` for production schema.

## Logging

JSON logs in non-development environments. Context fields: `request_id`, `user_id` when authenticated, `operation`, `duration_ms`, `status`. Passwords, JWT values, and refresh tokens are not logged.
