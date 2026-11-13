from fastapi import APIRouter
router = APIRouter(prefix="/workflows", tags=["workflows"])

@router.get("/")
def list_workflows():
    return {"items": []}
