"""AWS S3 service wrapper for file upload/download operations."""

import logging
import uuid

import boto3

from app.config import settings

logger = logging.getLogger(__name__)

_s3_client = None


def _get_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client("s3", region_name=settings.aws_region)
    return _s3_client


def upload_image(file_bytes: bytes, filename: str, content_type: str = "image/jpeg") -> str:
    """Upload a crop image to S3 and return the S3 key.

    Args:
        file_bytes: Raw file bytes
        filename: Original filename
        content_type: MIME type of the file

    Returns:
        S3 key of the uploaded file
    """
    client = _get_client()
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "jpg"
    s3_key = f"uploads/{uuid.uuid4()}.{ext}"

    client.put_object(
        Bucket=settings.s3_bucket_uploads,
        Key=s3_key,
        Body=file_bytes,
        ContentType=content_type,
    )
    logger.info("Uploaded image to s3://%s/%s", settings.s3_bucket_uploads, s3_key)
    return s3_key


def download_file(bucket: str, key: str) -> bytes:
    """Download a file from S3 and return its bytes."""
    client = _get_client()
    response = client.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()


def get_policy_document(s3_key: str) -> bytes:
    """Download a policy document from the policies bucket."""
    return download_file(settings.s3_bucket_policies, s3_key)


def get_uploaded_image(s3_key: str) -> bytes:
    """Download an uploaded crop image from the uploads bucket."""
    return download_file(settings.s3_bucket_uploads, s3_key)
