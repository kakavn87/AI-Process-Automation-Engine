# FastAPI Backend

The backend is organized by responsibility:
- `api`: HTTP routes
- `services`: process orchestration and OpenAI integration
- `engine`: analysis, workflow validation, and controlled execution
- `connectors`: external connector adapters and mock connectors
- `models`: SQLAlchemy persistence models
- `schemas`: API contracts
- `core`: configuration and infrastructure

## OpenAI LLM setup

The process analyzer uses the OpenAI Responses API with Structured Outputs. Configure these environment variables on the backend only:

- `OPENAI_API_KEY`: an API key from the OpenAI Platform
- `OPENAI_MODEL`: shared model identifier; defaults to `gpt-6-luna`
- `OPENAI_ANALYSIS_MODEL`: optional faster model for the initial process analysis; defaults to `OPENAI_MODEL`
- `OPENAI_OPTIMIZATION_MODEL`: optional model for redesigning the process after clarification; defaults to `OPENAI_MODEL`

For local development, copy `.env.example` to `.env` and add your key. Never commit `.env` or place the API key in the Angular frontend.

When `OPENAI_API_KEY` is empty, the service deliberately falls back to deterministic rules and reports `llmUsed=false`. When the API is unavailable, it logs the error and also falls back so the application remains usable.

## Human approval and execution

`POST /api/executions/` stores a workflow execution in the database with status `awaiting_approval`. A reviewer can then call:

- `POST /api/executions/{id}/approve`
- `POST /api/executions/{id}/reject`
- `GET /api/executions/{id}`

The current executor is intentionally simulation-only. Approval records the human decision and simulates each step; it does not send email, post to Teams, or contact external systems. The approval endpoints are a demo workflow and must be protected by authentication and role-based authorization before production use.
