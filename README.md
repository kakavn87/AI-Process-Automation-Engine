# AI Process Optimierung

AI Process Optimierung is a portfolio MVP that turns natural-language business process descriptions into structured workflow proposals, enforces a human approval gate, and records simulated execution events.

## What this demonstrates

- **Python / FastAPI** backend organized by API routes, application services, a process-analysis engine, connector boundaries, schemas, and SQLAlchemy persistence models.
- **Angular 19** standalone frontend using Angular Signals for process and execution state.
- **OpenAI Responses API or an OpenAI-compatible gateway** (including LiteLLM Proxy) with Pydantic Structured Outputs for LLM-based process understanding and workflow proposal generation.
- **Document intake** for PDF, DOCX, PPTX, XLSX, CSV, TXT, Markdown and common images. Text is extracted in memory; TIFF images, diagrams and scanned PDF pages can be passed to a vision-capable model.
- **Optional AI platform companion** using LiteLLM Proxy and OpenWebUI through a local Docker Compose profile.
- **Rules-based fallback** so the demo remains available when an OpenAI API key is not configured or the API is temporarily unavailable.
- **Human-in-the-loop approval lifecycle**: create an execution request, inspect workflow steps, approve or reject, and retain a decision note.
- **Server-side safety validation** that requires a human approval step before outbound email, Teams, or notification steps.
- **Simulation-only execution**: approved steps create an event log; no real email, Teams message, or external business action is sent.
- **Python tabular-data engine** for in-memory CSV/XLSX profiling, missing-value detection, numeric summaries, duplicate removal, and cleaned previews without LLM API usage.
- **Connector boundaries** for Outlook, document parsing, spreadsheets, and Teams. These are planned integrations, not live connections.

> This is a portfolio MVP, not a production-ready automation platform. Authentication/authorization, durable production database migrations, and live connector implementations must be added before real business processes are used.

## LLM configuration

The backend uses the OpenAI **Responses API** and schema-constrained Pydantic output. The default model is `gpt-6-luna`; it can be changed with `OPENAI_MODEL`. Set optional `OPENAI_BASE_URL` to an OpenAI-compatible gateway such as LiteLLM Proxy. When a gateway is used, `OPENAI_API_KEY` must be a least-privilege virtual key issued by that gateway. The provider API key must never be sent to the browser.

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

- `OPENAI_API_KEY`: your provider API key, or a least-privilege LiteLLM virtual key (secret)
- `OPENAI_MODEL`: `gpt-6-luna` or the exact model alias exposed by your gateway
- `OPENAI_BASE_URL`: optional private OpenAI-compatible gateway URL, e.g. LiteLLM's `https://gateway.example/v1`
- `OPENWEBUI_URL`: optional URL of a separately deployed OpenWebUI portal

Save the environment changes to trigger a redeploy. The frontend never receives the API key.

## API

- `POST /api/processes/analyze` — analyze a text business-process description.
- `POST /api/processes/analyze-with-documents` — analyze a description plus up to 8 PDF, DOCX, PPTX, XLSX, CSV, TXT, Markdown, PNG, JPG, WEBP, TIFF, Draw.io, BPMN, SVG and XML files (10 MB per file, 25 MB combined).
- `GET /api/integrations/readiness` — return non-secret readiness for the AI gateway, optional OpenWebUI portal and business connector catalog.
- `POST /api/data-processing/upload` — upload a CSV or XLSX file (max 10 MB) for in-memory data profiling and a cleaned preview.
- `POST /api/executions/` — create an execution record and pause at human approval.
- `GET /api/executions/` — list execution records.
- `GET /api/executions/{id}` — retrieve one execution record.
- `POST /api/executions/{id}/approve` — record approval and an optional note; run the workflow in simulation mode.
- `POST /api/executions/{id}/reject` — reject the request and record an optional note.
- `GET /api/executions/live-readiness` — check whether the administrator-configured webhook is ready.
- `POST /api/executions/{id}/live` — dispatch the approved workflow to that webhook after separate explicit confirmation.

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
- `POST /api/processes/sessions/{id}/knowledge/search` — search only the current process session's indexed document chunks (RAG must be enabled).
- `DELETE /api/processes/sessions/{id}` — delete the session and its Qdrant vectors, when indexed.
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

## Step 1: document and diagram intake

The process builder accepts optional source files alongside a short description. Text is extracted from PDF, DOCX, PPTX, XLSX, CSV, TXT and Markdown files. PNG/JPG/WEBP/TIFF images, SVG, Draw.io and BPMN/XML diagram labels and edges, slide pictures, and PDF pages containing scanned or visual content are extracted or normalized and sent to a configured vision-capable model. Original uploaded files are processed in memory and are not persisted. When optional RAG is enabled, extracted text chunks and source metadata are stored in Qdrant under the generated process-session ID; this is session-scoped, not a reusable cross-workspace knowledge base. A scanned image-only submission requires a configured vision-capable model. The app displays source filenames and extraction warnings with the analysis.

The upload limit is 8 files, 10 MB per file and 25 MB combined. Office archives are checked for expanded-size limits. All supplied document content is treated as untrusted input by the analysis prompt.

**RAG / vector-store note:** an optional Qdrant-backed, process-session-scoped RAG service is now implemented. It chunks extracted document text with source filename/page metadata, creates embeddings through the configured OpenAI-compatible gateway, filters retrieval by the server-generated process session ID, records embedding token usage, and supports deleting a session's vectors. RAG remains disabled by default. Do not enable it for a public multi-user deployment until authentication, tenant/workspace authorization, access checks on every session endpoint, retention policies and production-grade deletion controls are implemented. The current MVP does not yet provide customer identity or tenant isolation.

Local RAG configuration (after copying the backend environment file):
```env
RAG_ENABLED=true
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=flowpilot_process_knowledge
RAG_EMBEDDING_MODEL=text-embedding-3-small
RAG_VECTOR_SIZE=1536
```
With the included LiteLLM profile, set `OPENAI_BASE_URL=http://localhost:4000/v1`, `AI_GATEWAY_PROVIDER=litellm`, `OPENAI_MODEL=process-analysis`, `OPENAI_VISION_MODEL=process-vision`, and `RAG_EMBEDDING_MODEL=process-embeddings`. Set `OPENAI_API_KEY` to a separate least-privilege LiteLLM virtual key. Do not use the LiteLLM master key in the application.

## Optional local LiteLLM + OpenWebUI profile

The backend can call LiteLLM Proxy through the same OpenAI-compatible Responses API client. OpenWebUI can use the same gateway for employee chat and assistant experiments. These are optional companion services and are not deployed automatically to the public Render demo.

1. Copy `infrastructure/docker/.env.ai-platform.example` to `infrastructure/docker/.env.ai-platform` and set a provider API key plus a long random LiteLLM master key.
   The example starts with local-only PostgreSQL, LiteLLM, Qdrant and Open WebUI ports. Change the example database password and all secrets before using anything beyond a local development machine.
2. Start LiteLLM and the local key database:
   `docker compose --env-file infrastructure/docker/.env.ai-platform -f infrastructure/docker/docker-compose.yml --profile ai-platform up -d litellm`
   Generate a separate backend virtual key as well. Set the backend key in `backend/.env` as `OPENAI_API_KEY`; do not use the LiteLLM master key in either client. For RAG, start Qdrant with:
   `docker compose --env-file infrastructure/docker/.env.ai-platform -f infrastructure/docker/docker-compose.yml --profile ai-platform up -d qdrant`
   Then set `RAG_ENABLED=true`, `QDRANT_URL=http://localhost:6333`, `AI_GATEWAY_PROVIDER=litellm`, `OPENAI_BASE_URL=http://localhost:4000/v1`, `OPENAI_MODEL=process-analysis`, `OPENAI_VISION_MODEL=process-vision`, and `RAG_EMBEDDING_MODEL=process-embeddings` in `backend/.env`.
3. Generate a least-privilege LiteLLM virtual key for OpenWebUI, then set it as `LITELLM_WEBUI_KEY` in the env file and start OpenWebUI:
   `docker compose --env-file infrastructure/docker/.env.ai-platform -f infrastructure/docker/docker-compose.yml --profile ai-platform up -d open-webui`
4. For a backend running on the host, set `OPENAI_BASE_URL=http://localhost:4000/v1`, `OPENAI_MODEL=process-analysis`, and `OPENAI_API_KEY` to a separate LiteLLM virtual key. Set `OPENWEBUI_URL=http://localhost:3000` to show the portal link in Step 6.

The LiteLLM config exposes separate aliases: `process-analysis`, `process-vision` and `process-embeddings`. The local profile now includes PostgreSQL for LiteLLM virtual-key management/spend tracking and Qdrant for optional FlowPilot RAG. Qdrant, LiteLLM and Open WebUI ports are bound to localhost. Create separate least-privilege virtual keys for the FlowPilot backend and Open WebUI via LiteLLM's `/key/generate` endpoint; allow only the three model aliases each client needs. For the backend, set the environment variables described above. For Open WebUI, set `LITELLM_WEBUI_KEY` to its own scoped key. Open WebUI requires login. Do not expose the LiteLLM master key or an admin gateway port publicly. For production, deploy these services on private infrastructure with TLS, authentication, persistent storage, monitoring and least-privilege keys. A Render deployment needs separately provisioned services and secrets; this repository change does not create billable services or copy secrets to Render.

## Step 6: integration center and opt-in live webhook dispatch

Step 6 now surfaces the configured AI model gateway (direct provider or LiteLLM), an optional OpenWebUI portal link, the configured webhook handoff and a catalog of future business connectors. Microsoft 365, SAP/ERP and per-workspace Custom REST connectors are displayed as planned, not as working connections. Their OAuth flows and customer-managed credential storage are not implemented yet.

The approved workflow still completes in simulation mode first. A separate Step 6 can hand off the approved workflow structure to one administrator-configured HTTPS webhook. This is an integration boundary, not a built-in CRM, ticketing, email, or Teams connector.

Live dispatch is disabled by default. To enable it on the Backend service, configure these environment variables:

- `WEBHOOK_EXECUTION_ENABLED=true`
- `WORKFLOW_WEBHOOK_URL=https://your-company.example/webhook`
- `WORKFLOW_WEBHOOK_BEARER_TOKEN` (recommended for protected receivers)
- `WORKFLOW_LIVE_EXECUTION_TOKEN` (required operator confirmation secret; entered in the UI at dispatch time)
- `WORKFLOW_WEBHOOK_TIMEOUT_SECONDS=10` (optional)

The endpoint is server-side configuration only; browser users cannot supply or change the destination. HTTPS is required, URL-embedded credentials and local/internal hostnames or IP addresses are rejected, and redirects are not followed. The frontend requires the operator confirmation secret plus a separate confirmation checkbox before dispatch. The operator secret is checked server-side, is not sent to the receiving webhook, and is cleared from the UI after a successful dispatch. PR previews forcibly clear webhook configuration and can never send live requests.

The webhook receives an event name, execution ID/name, workflow name/trigger, and step metadata (IDs, types, names, descriptions, connector name, and approval requirement). The original process description, clarification answers, AI credentials, and bearer token are not included. Configure the receiver to validate the bearer token, deduplicate by `execution.id`, and apply its own authorization and business rules.

Each execution permits only one recorded live dispatch attempt. A timeout is marked `unknown`, because the receiving system may have processed the request even when no response arrived; the app blocks automatic retries to avoid duplicate side effects. A non-2xx response is recorded as failed and must be investigated in the receiver's logs. A 2xx response is recorded as confirmed receipt, not proof that every downstream business action completed.

The live webhook endpoint is exposed as `GET /api/executions/live-readiness` and `POST /api/executions/{id}/live`. The POST body requires `{"confirm_live_execution": true, "confirmation_token": "…"}`; the confirmation token is validated against the backend environment secret and never forwarded to the receiver. The app is still a single-user MVP without full account authentication or tenant-level authorization. Keep live execution disabled in public demos unless the operator-token control and receiving-system protections are appropriate for the intended environment. For production use, implement account authentication, role-based authorization, tenant isolation, idempotency at the receiver, and a security review.

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
