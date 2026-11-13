# Database and schema migrations

## Current deployment state

The public Render demo remains on SQLite until a managed PostgreSQL connection is explicitly configured. SQLite on an ephemeral Render web-service filesystem is suitable only for the demo and is not durable production storage.

The backend accepts:
- `postgresql+psycopg://...` (preferred explicit SQLAlchemy URL)
- `postgresql://...`
- `postgres://...` (common provider URL form)

The latter two are normalized to the installed psycopg v3 SQLAlchemy dialect. Never place a real database URL or password in Git.

## What the migration baseline does

The first Alembic revision is a compatibility baseline. Before the application serves requests, it runs `alembic upgrade head`. Its first revision uses `Base.metadata.create_all(checkfirst=True)`:
- Existing SQLite tables are detected and left in place.
- Missing tables are created.
- A fresh PostgreSQL database receives the current mapped schema.
- The Alembic version table records the baseline revision.

Future model/schema changes must be shipped as new, explicit Alembic revisions. Do not edit the baseline after it has been applied to a persistent database.

## Local PostgreSQL

The repository Compose file already includes a local PostgreSQL service bound to loopback. From the repository root:

```bash
docker compose -f infrastructure/docker/docker-compose.yml up -d postgres
```

Then from `backend/`, set a local-only URL in `.env`:

```env
DATABASE_URL=postgresql+psycopg://app:app@localhost:5432/process_automation
```

Run migrations and start the API:

```bash
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

## Render PostgreSQL cutover

1. Provision PostgreSQL in the same region as the Backend service. Prefer the provider's private/internal connection URL.
2. Set the Backend service's `DATABASE_URL` environment variable to the PostgreSQL URL. Treat it as a secret.
3. Do not set `PREVIEW_DATABASE_URL` to the Production database. A pull-request preview with a remote Production URL refuses to start unless a distinct Preview database is supplied.
4. Deploy and verify the Backend health endpoint, then create and retrieve a test workflow session.
5. If existing SQLite records matter, export and import them into PostgreSQL with a reviewed data-transfer script before switching users. Changing `DATABASE_URL` alone does not copy existing data.

The application does not provision Render databases or change a service's secret environment variables automatically. This avoids creating billable infrastructure or exposing credentials without an explicit operator action.

## Downgrades

The initial baseline downgrade drops all application tables. Do not run `alembic downgrade base` against a database containing records that must be retained. Production migrations should be additive where practical, with a tested backup and rollback plan.
