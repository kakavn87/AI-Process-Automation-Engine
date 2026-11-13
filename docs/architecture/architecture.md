# Architecture

This project uses a feature/domain-oriented structure.

## Backend

FastAPI API routes -> application services -> process/workflow engines -> connectors and persistence.

## Frontend

Angular pages/components -> Signal stores -> services -> HTTP API.

## AI and knowledge services

- LiteLLM is the preferred OpenAI-compatible gateway for analysis, vision and embeddings.
- Open WebUI is an optional internal AI workspace; it is not required by the Angular product UI.
- PostgreSQL with pgvector stores persistent document chunks and embeddings when the private knowledge feature is enabled.
- The existing in-memory document analysis remains the default for the public demo.

See flowpilot-part-1-6.md for the detailed data flow, RAG lifecycle, deployment steps and security limits.
