from fastapi import APIRouter
from app.api.routes.health import router as health_router
from app.api.routes.processes import router as processes_router
from app.api.routes.workflows import router as workflows_router
from app.api.routes.executions import router as executions_router
from app.api.routes.data_processing import router as data_processing_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(processes_router)
api_router.include_router(workflows_router)
api_router.include_router(executions_router)
api_router.include_router(data_processing_router)
