from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.database import Base, engine
import app.models  # noqa: F401 - registers SQLAlchemy models with Base.metadata


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="Analyze business processes and prepare controlled automation workflows.",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/", tags=["system"])
def root():
    return {
        "name": settings.APP_NAME,
        "status": "running",
        "version": "0.2.0",
        "llmConfigured": bool(settings.OPENAI_API_KEY.strip()),
        "llmModel": settings.OPENAI_MODEL,
        "docs": "/docs",
    }
