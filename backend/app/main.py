from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.core.config import settings
from app.core.database import SessionLocal
from app.dependencies.auth import get_tenant_context
from app.services.auth_service import AuthService
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run versioned schema changes before the API accepts traffic. This also
    # protects Render services whose dashboard start command predates this
    # repository's updated render.yaml.
    backend_dir = Path(__file__).resolve().parents[1]
    alembic_config = Config(str(backend_dir / "alembic.ini"))
    command.upgrade(alembic_config, "head")
    if settings.AUTH_ENABLED:
        with SessionLocal() as db:
            AuthService(db).bootstrap()
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

# Health and sign-in bootstrap stay public. All business APIs require an
# authenticated tenant context when AUTH_ENABLED is switched on.
app.include_router(health_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(
    api_router,
    prefix="/api",
    dependencies=[Depends(get_tenant_context)],
)


@app.get("/", tags=["system"])
def root():
    return { "name": settings.APP_NAME, "status": "running", "docs": "/docs" }
