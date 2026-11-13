# Architecture

This project uses a feature/domain-oriented structure rather than one mandatory FastAPI layout.

## Backend
API -> Services -> Domain Engine -> Connectors / Persistence

## Frontend
Pages/Components -> Signal Store -> Services -> HTTP API

The structure can evolve with team size, domain complexity, deployment model, and organizational conventions.
