# AI Process Automation Engine

A portfolio MVP that turns natural-language business process descriptions into structured workflow proposals, enforces a human approval gate, and records simulated execution events.

## What this demonstrates

- **Python / FastAPI** backend organized by API routes, application services, a process-analysis engine, connector boundaries, schemas, and SQLAlchemy persistence models.
- **Angular 19** standalone frontend using Angular Signals for process and execution state.
- **OpenAI Responses API** with Pydantic Structured Outputs for LLM-based process understanding and workflow proposal generation.
- **Rules-based fallback** so the demo remains available when an OpenAI API key is not configured or the API is temporarily unavailable.
- **Human-in-the-loop approval lifecycle**: create an execution request, inspect workflow steps, approve or reject, and retain a decision note.
- **Server-side safety validation** that requires a human approval step before outbound email, Teams, or notification steps.
- **Simulation-only execution**: approved steps create an event log; no real email, Teams message, or external business action is sent.
- **Python tabular-data engine** for in-memory CSV/XLSX profiling, missing-value detection, numeric summaries, duplicate removal, and cleaned previews without LLM API usage.
- **Connector boundaries** for Outlook, document parsing, spreadsheets, and Teams. These are planned integrations, not live connections.

> This is a portfolio MVP, not a production-ready automation platform. Authentication/authorization, durable production database migrations, and live connector implementations must be added before real business processes are used.

## LLM configuration

The backend uses the OpenAI **Responses API** and schema-constrained Pydantic output. The default model is `gpt-6-luna`, selected as a cost-sensitive model for focused, high-volume tasks. The model can be changed with `OPENAI_MODEL`.

The deterministic analyzer continues to provide the baseline automation score and canonical signals. When the key is configured, the LLM generates the process summary, current process, automation opportunities, integrations, risks, assumptions, questions, and proposed workflow.

Set `OPENAI_API_KEY` in the backend environment. Do not commit the key to Git or place it in the Angular frontend.

### Local setup

Copy `backend/.env.example` to `backend/.env`, then add your API key:

```env
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=gpt-6-luna
```

When `OPENAI_API_KEY` is empty, the API returns `llmUsed: false` and uses deterministic rules. A successful model call returns `llmUsed: true`. If the model request fails, the backend logs the exception and falls back to deterministic analysis.

### Render setup

In the Render Dashboard, open the backend service's **Environment** page and add:

- `OPENAI_API_KEY`: your OpenAI API key (secret)
- `OPENAI_MODEL`: `gpt-6-luna` (optional; this is already the backend default)

Save the environment changes to trigger a redeploy. The frontend never receives the API key.

## API

- `POST /api/processes/analyze` — analyze a business process and return the workflow proposal.
- `POST /api/data-processing/upload` — upload a CSV or XLSX file (max 10 MB) for in-memory data profiling and a cleaned preview.
- `POST /api/executions/` — create an execution record and pause at human approval.
- `GET /api/executions/` — list execution records.
- `GET /api/executions/{id}` — retrieve one execution record.
- `POST /api/executions/{id}/approve` — record approval and an optional note; run the workflow in simulation mode.
- `POST /api/executions/{id}/reject` — reject the request and record an optional note.

Execution states:
- `awaiting_approval`
- `completed` (simulation only)
- `rejected`

No real email or Teams message is sent after approval.

## Interactive workflow lifecycle

`POST /api/processes/analyze` now persists the analysis as a workflow session and returns `processSessionId`, `workflowStatus`, and `openQuestions`. The Angular app opens the session page automatically.

Session lifecycle:
- `needs_input` — the user can answer the generated open questions. Partial answers are saved.
- `processing` — the server validates answers and updates the workflow context with deterministic Python logic.
- `ready_for_approval` — the updated workflow is ready for a human review.
- `awaiting_approval` — an approval request exists and execution is paused.
- `completed` / `rejected` / `failed` — terminal results.

Additional endpoints:
- `GET /api/processes/sessions/{id}` — retrieve the persisted session, answers, questions, status, and audit events.
- `POST /api/processes/sessions/{id}/answers` — submit answers as `{"answers": {"q-id": "value"}}`. The server validates only known question IDs and allows partial submissions.
- `POST /api/processes/sessions/{id}/execute` — create the approval request after preparation is complete.
- `GET /api/monitoring/usage` — retrieve aggregate AI token usage and recent provider events.

When the required answers are complete, Python updates the process specification and proposed workflow context without making another LLM call. The user then explicitly creates an approval request. Approving it continues the existing simulation lifecycle; rejecting it records the decision and runs no steps.

## AI usage and estimated costs

Each OpenAI process-analysis attempt records provider, model, status, duration, and token usage when the provider returns usage metadata. Failed calls are marked as fallback events. If a provider response exists but structured-output parsing fails, its usage metadata is retained.

Estimated USD cost is calculated only when both of these backend environment variables are configured:
- `OPENAI_INPUT_USD_PER_1M` — input-token price per million tokens.
- `OPENAI_OUTPUT_USD_PER_1M` — output-token price per million tokens.

Both values default to unset. Until valid prices are configured, the monitoring endpoint shows token totals but leaves estimated cost unavailable. This avoids inventing a model price or presenting a token estimate as an invoice amount.

## Safe Render pull request previews

The Frontend and Backend services use Render's automatic pull request service previews. The Angular build generates `runtime-config.js` before each deploy:

- Production builds use `API_BASE_URL` (or the configured Production backend URL).
- PR builds detect Render's `IS_PULL_REQUEST` and `RENDER_EXTERNAL_HOSTNAME` values and derive the matching Backend Preview URL from the PR suffix.
- If the matching Backend Preview URL cannot be identified, the Frontend fails closed and does not fall back to the Production API.

The Backend also detects `IS_PULL_REQUEST`:

- Preview CORS allows only the Frontend Preview for the same PR, not the Production frontend or arbitrary websites.
- If Production currently uses SQLite, the Preview uses a different SQLite file on its own temporary service filesystem.
- If Production is later moved to a remote database, the Preview refuses to start unless `PREVIEW_DATABASE_URL` is explicitly set to a separate test database.
- PR previews ignore the Production `OPENAI_API_KEY`; set `PREVIEW_OPENAI_API_KEY` on a Preview instance to use a separate test key. Otherwise, deterministic fallback is used.

Render service previews initially copy their base service settings, including environment variables. Do not add a persistent disk or shared Production datastore to a Preview service. These previews are temporary and are deleted when their PR is merged or closed. This application still has no authentication; do not enter real customer or confidential business data in a public Preview.

## Safety and production boundaries

The action dispatcher remains simulation-only. Approval records authorization for the demo workflow, but it does not send email, post to Teams, invoke HTTP endpoints, or modify an external business system. Live connectors must be implemented and separately configured before those actions can be enabled.

The new session and usage endpoints are currently intended for this single-user portfolio MVP. Authentication, tenant isolation, role-based approval permissions, durable migrations, retention controls, and production-grade audit/security reviews are still required before exposing business data to multiple users.

## Run locally

### Backend

```bash
cd backend
python -m venv .venv
# macOS / Linux: source .venv/bin/activate
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
cp .env.example .env  # Windows: copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

API documentation: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm start
```

Open http://localhost:4200.

### Tests

```bash
cd backend
pytest
```

## Deployment (Render)

The root `render.yaml` defines the FastAPI backend and Angular static frontend. The frontend's production environment points to the deployed backend URL; the backend CORS allow-list includes the deployed frontend URL.

The current Free service uses SQLite for the approval demo. SQLite data on an ephemeral web-service filesystem is not a durable production store. Use managed PostgreSQL and migration tooling before storing important business records.

## Project structure

```text
backend/app/
  api/             HTTP routes and API router
  core/            settings, database, logging, security
  connectors/      connector interfaces and implementations
  dependencies/    FastAPI dependencies
  engine/          analyzer, workflow, execution engine
  models/           SQLAlchemy persistence models
  schemas/          Pydantic request/response schemas
  services/         application orchestration and LLM provider
frontend/src/app/
  core/             shared API access and API models
  features/         process, workflow, execution features and stores
  shared/           reusable UI components
```
