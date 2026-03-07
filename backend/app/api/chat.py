"""Chat endpoint — invokes the LangGraph ReAct agent."""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agent.nodes import invoke_agent
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    image_key: str | None = None
    farmer_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    tools_used: list[str]
    farmer_id: str


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a message to the AgriMitra agent and get a response.

    Optionally include an image_key (from /api/upload) for crop image analysis.
    """
    if not request.message.strip() and not request.image_key:
        raise HTTPException(status_code=400, detail="Message or image required")

    farmer_id = request.farmer_id or settings.default_farmer_id

    try:
        result = await invoke_agent(
            message=request.message,
            farmer_id=farmer_id,
            image_key=request.image_key,
        )
        return ChatResponse(**result)
    except Exception as e:
        logger.error("Chat error: %s", e)
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")
