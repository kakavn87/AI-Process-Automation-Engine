# AI Process Automation Engine

A portfolio MVP demonstrating how a business process can be analyzed, translated into a workflow, validated, and prepared for controlled automation with human approval.

## What this demonstrates

- **Python / FastAPI** backend organized by API, services, domain engine, connectors, schemas, and persistence models.
- **Angular 19** standalone frontend organized by feature.
- **Angular Signals** stores for process, workflow, and execution state.
- **Connector boundary** with safe mock connectors and placeholders for Microsoft Graph integrations.
- **Human approval** as an explicit workflow gate before consequential execution.

> This is a portfolio MVP, not a production-ready autonomous agent. Process analysis currently uses deterministic heuristics; the OpenAI integration and Microsoft Graph connector modules are extension points. No real email, Teams, or external business action is sent by the demo.

## Architecture

```text
Angular UI (Signals stores)
        |
        v
FastAPI routes -> Application services
                       |
                       +-> Process analyzer
                       +-> Workflow generator / validator
                       +-> Workflow executor
                       +-> Connector interfaces
                                +-> Mock connectors
                                +-> Microsoft Graph (future integration)
```

See [architecture notes](docs/architecture/architecture.md).

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

API docs: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm start
```

Open http://localhost:4200.

## Deployment (Render blueprint)

The repository includes `infrastructure/render/render.yaml` as a starting point for the backend service. In Render, create a Blueprint from this repository and select that YAML file. The frontend can be deployed as a Static Site with:

- Root directory: `frontend`
- Build command: `npm ci && npm run build`
- Publish directory: `dist/ai-process-automation-engine/browser`

Update `frontend/src/environments/environment.prod.ts` to the actual backend URL and set the backend `CORS_ORIGINS` environment variable to the actual frontend URL. Because the current backend uses SQLite, its database is demo-only and may be ephemeral on hosts with ephemeral filesystems. Use managed PostgreSQL before treating stored data as durable.

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
  services/         application orchestration
frontend/src/app/
  core/             shared API access and API models
  features/         process, workflow, execution features and stores
  shared/           reusable UI components
```

## Status

The current version is an architectural and functional scaffold. The process analyzer provides a rule-based score, while persistence, full workflow CRUD, authentication, real AI-driven workflow generation, approval UI, and live Microsoft Graph actions remain planned work.
