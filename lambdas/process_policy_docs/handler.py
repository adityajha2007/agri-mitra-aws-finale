"""Lambda: Process new policy documents uploaded to S3.

Triggered by S3 PutObject events on the policies bucket.
Generates embeddings and stores metadata in DynamoDB for RAG.
"""

import json
import logging
import os
from datetime import datetime, timezone

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "agri-mitra-policy-documents")
BEDROCK_EMBEDDING_MODEL = os.environ.get(
    "BEDROCK_EMBEDDING_MODEL", "amazon.titan-embed-text-v2:0"
)
AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")

s3_client = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)


def _generate_embedding(text: str) -> list[float]:
    """Generate embedding using Bedrock Titan Embed."""
    # Truncate to model's max input length
    text = text[:8000]
    response = bedrock.invoke_model(
        modelId=BEDROCK_EMBEDDING_MODEL,
        contentType="application/json",
        accept="application/json",
        body=json.dumps({"inputText": text}),
    )
    result = json.loads(response["body"].read())
    return result["embedding"]


def _extract_metadata(key: str, content: str) -> dict:
    """Extract basic metadata from the document path and content."""
    parts = key.replace(".txt", "").replace(".pdf", "").replace(".md", "").split("/")

    # Try to extract category and state from path structure
    # Expected format: policies/{category}/{state}/{filename}
    category = parts[1] if len(parts) > 2 else "general"
    state = parts[2] if len(parts) > 3 else "central"
    title = parts[-1].replace("-", " ").replace("_", " ").title()

    # Try to detect language from content
    language = "en"
    hindi_chars = sum(1 for c in content[:500] if "\u0900" <= c <= "\u097F")
    if hindi_chars > 50:
        language = "hi"

    return {
        "category": category,
        "state": state,
        "title": title,
        "language": language,
    }


def handler(event, context):
    """Process S3 event for new policy documents."""
    logger.info("Processing policy document event: %s", json.dumps(event))

    table = dynamodb.Table(DYNAMODB_TABLE)
    processed = 0

    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]

        # Skip non-document files
        if not any(key.endswith(ext) for ext in [".txt", ".md", ".pdf"]):
            logger.info("Skipping non-document file: %s", key)
            continue

        try:
            # Download document
            response = s3_client.get_object(Bucket=bucket, Key=key)
            content = response["Body"].read().decode("utf-8", errors="ignore")

            if not content.strip():
                logger.warning("Empty document: %s", key)
                continue

            # Extract metadata
            metadata = _extract_metadata(key, content)

            # Generate embedding from document content
            embedding = _generate_embedding(content)

            # Store in DynamoDB
            doc_id = key.replace("/", "_").replace(".", "_")
            item = {
                "doc_id": doc_id,
                "s3_key": key,
                "title": metadata["title"],
                "category": metadata["category"],
                "state": metadata["state"],
                "language": metadata["language"],
                "embedding": embedding,
                "embedding_status": "completed",
                "content_length": len(content),
                "processed_at": datetime.now(timezone.utc).isoformat(),
            }
            table.put_item(Item=item)
            processed += 1

            logger.info("Processed document: %s (embedding dim: %d)", key, len(embedding))

        except Exception as e:
            logger.error("Error processing %s: %s", key, e)
            # Mark as failed in DynamoDB
            try:
                doc_id = key.replace("/", "_").replace(".", "_")
                table.put_item(
                    Item={
                        "doc_id": doc_id,
                        "s3_key": key,
                        "embedding_status": "failed",
                        "error": str(e),
                        "processed_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
            except Exception:
                pass
            continue

    logger.info("Processed %d documents", processed)
    return {"statusCode": 200, "body": f"Processed {processed} documents"}
