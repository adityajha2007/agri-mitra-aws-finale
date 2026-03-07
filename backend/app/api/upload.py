"""Image upload endpoint — stores crop images in S3."""

import logging

from fastapi import APIRouter, HTTPException, UploadFile

from app.services import s3

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.post("/upload")
async def upload_image(file: UploadFile):
    """Upload a crop image to S3 for analysis.

    Returns the S3 key which can be passed to the /api/chat endpoint
    for crop disease diagnosis.
    """
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Allowed: JPEG, PNG, WebP",
        )

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Max size: 10 MB")

    try:
        s3_key = s3.upload_image(
            file_bytes=contents,
            filename=file.filename or "upload.jpg",
            content_type=file.content_type or "image/jpeg",
        )
        return {"s3_key": s3_key, "filename": file.filename}
    except Exception as e:
        logger.error("Upload error: %s", e)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
