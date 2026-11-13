from fastapi import APIRouter
router = APIRouter(prefix="/executions", tags=["executions"])

@router.get("/")
def list_executions():
    return {"items": []}
