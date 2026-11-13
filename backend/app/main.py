from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.database import Base, engine
from app.models.execution import ApprovalExecution  # noqa: F401 - registers the table
from app.models.workflow_session import AIUsageEvent, WorkflowSession  # noqa: F401 - register tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="Analyze business processes and prepare controlled automation workflows.",
    version="0.3.0",
    lifespan=lifespan,
)

cors_options = {
    "allow_origins": [] if settings.IS_PULL_REQUEST else settings.cors_origin_list,
    "allow_credentials": True,
    "allow_methods": ["GET", "POST", "OPTIONS"],
    "allow_headers": ["*"],
}

if settings.IS_PULL_REQUEST and settings.preview_cors_origin_regex:
    cors_options["allow_origin_regex"] = settings.preview_cors_origin_regex

app.add_middleware(CORSMiddleware, **cors_options)

app.include_router(api_router, prefix="/api")


@app.get("/", tags=["system"])
def root():
    return { "name": settings.APP_NAME, "status": "running", "docs": "/docs" }
