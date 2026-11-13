# FastAPI Backend

The backend is intentionally organized by responsibility:
- `api`: HTTP routes
- `services`: application/business orchestration
- `engine`: process automation domain logic
- `connectors`: external integrations
- `models`: SQLAlchemy persistence models
- `schemas`: Pydantic API contracts
- `core`: configuration and infrastructure

There is no single mandatory FastAPI structure. This is a scalable starting point for a feature/domain-oriented application.
