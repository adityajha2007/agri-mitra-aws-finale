"""AgriMitra agent state definition for LangGraph."""

from typing import Annotated, Optional
from typing_extensions import TypedDict

from langgraph.graph.message import add_messages


class AgriMitraState(TypedDict):
    """State for the AgriMitra ReAct agent.

    The messages field uses LangGraph's add_messages reducer to automatically
    append new messages to the conversation history.
    """

    messages: Annotated[list, add_messages]
    farmer_id: str
    language: Optional[str]
    location: Optional[str]
    image_keys: list[str]
