"""AWS Bedrock service wrapper for model invocation, embeddings, and vision."""

import json
import base64
import logging

import boto3

from app.config import settings

logger = logging.getLogger(__name__)

_bedrock_client = None


def _get_client():
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = boto3.client(
            "bedrock-runtime", region_name=settings.aws_region
        )
    return _bedrock_client


def generate_embeddings(text: str) -> list[float]:
    """Generate text embeddings using Amazon Titan Embed."""
    client = _get_client()
    response = client.invoke_model(
        modelId=settings.bedrock_embedding_model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps({"inputText": text}),
    )
    result = json.loads(response["body"].read())
    return result["embedding"]


def analyze_image(image_bytes: bytes, prompt: str, media_type: str = "image/jpeg") -> str:
    """Analyze an image using Bedrock Claude Vision.

    Args:
        image_bytes: Raw image bytes
        prompt: Analysis prompt to send with the image
        media_type: MIME type of the image

    Returns:
        Text analysis from Claude Vision
    """
    client = _get_client()
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4096,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_b64,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    }

    response = client.invoke_model(
        modelId=settings.bedrock_vision_model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body),
    )
    result = json.loads(response["body"].read())
    return result["content"][0]["text"]


def invoke_model(prompt: str, system: str = "") -> str:
    """Invoke Bedrock Claude for text generation (non-agent use cases)."""
    client = _get_client()

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        body["system"] = system

    response = client.invoke_model(
        modelId=settings.bedrock_model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body),
    )
    result = json.loads(response["body"].read())
    return result["content"][0]["text"]
