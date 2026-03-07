"""Crop image analysis tool using Bedrock Claude Vision."""

import logging

from langchain_core.tools import tool

from app.services import bedrock, s3

logger = logging.getLogger(__name__)

IMAGE_ANALYSIS_PROMPT = """You are an expert agricultural scientist and plant pathologist.
Analyze this crop image and provide:

1. **Crop Identification**: What crop is shown (if identifiable)
2. **Health Assessment**: Overall health status (Healthy / Mild Issue / Moderate Issue / Severe Issue)
3. **Disease/Pest Detection**: Any visible diseases, pest damage, or nutrient deficiencies
4. **Diagnosis**: Specific disease/condition name if identifiable
5. **Recommended Treatment**: Practical treatment steps the farmer can take
6. **Preventive Measures**: Steps to prevent recurrence

Keep the language simple and practical for a farmer. If you cannot identify the issue clearly, say so and recommend consulting a local agricultural officer."""


@tool
def analyze_crop_image(s3_key: str) -> str:
    """Analyze a crop image for diseases, pests, and health issues.

    Use this tool when the farmer uploads an image of their crop and wants
    diagnosis or advice about visible issues like yellowing leaves, spots,
    pest damage, wilting, etc.

    Args:
        s3_key: The S3 key of the uploaded crop image

    Returns:
        Detailed analysis of the crop image including diagnosis and treatment
    """
    try:
        image_bytes = s3.get_uploaded_image(s3_key)

        # Determine media type from extension
        ext = s3_key.rsplit(".", 1)[-1].lower() if "." in s3_key else "jpg"
        media_type_map = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "webp": "image/webp",
        }
        media_type = media_type_map.get(ext, "image/jpeg")

        analysis = bedrock.analyze_image(
            image_bytes=image_bytes,
            prompt=IMAGE_ANALYSIS_PROMPT,
            media_type=media_type,
        )
        return analysis

    except Exception as e:
        logger.error("Image analysis error: %s", e)
        return f"Error analyzing crop image: {str(e)}. Please try uploading the image again."
