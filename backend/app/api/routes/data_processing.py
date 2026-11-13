import logging

from typing import Literal

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services.tabular_data_service import MAX_UPLOAD_BYTES, TabularDataService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data-processing", tags=["data-processing"])
service = TabularDataService()


@router.post("/upload")
async def upload_tabular_file(file: UploadFile = File(...), language: Literal["de", "en"] = "de"):
    filename = file.filename or ""
    try:
        if not filename:
            raise HTTPException(status_code=400, detail="Please choose a file to upload.")

        content = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="File is larger than the 10 MB upload limit.")

        try:
            return service.process(filename, content, language=language)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception("Unexpected error while processing uploaded tabular data.")
            raise HTTPException(
                status_code=400,
                detail="The file could not be processed. Check the file format and try again.",
            ) from exc
    finally:
        await file.close()
