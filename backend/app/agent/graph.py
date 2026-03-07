"""LangGraph ReAct agent construction for AgriMitra."""

from langchain_aws import ChatBedrockConverse
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from app.agent.prompts import SYSTEM_PROMPT
from app.config import settings
from app.tools.policy_search import search_policies
from app.tools.image_analysis import analyze_crop_image
from app.tools.mandi_prices import query_mandi_prices
from app.tools.weather import get_weather
from app.tools.news import get_agri_news
from app.tools.calculator import calculate

_agent = None


def build_agent():
    """Build and return the AgriMitra LangGraph ReAct agent.

    Uses create_react_agent which implements the ReAct loop:
    1. Reasoner: Claude analyzes the conversation and decides on next action
    2. Tool executor: Executes the selected tool
    3. Observer: Results fed back to Claude
    4. Done check: If no more tool calls, return final response
    """
    llm = ChatBedrockConverse(
        model=settings.bedrock_model_id,
        region_name=settings.aws_region,
        temperature=0.3,
        max_tokens=4096,
    )

    tools = [
        search_policies,
        analyze_crop_image,
        query_mandi_prices,
        get_weather,
        get_agri_news,
        calculate,
    ]

    checkpointer = MemorySaver()

    return create_react_agent(
        model=llm,
        tools=tools,
        state_modifier=SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )


def get_agent():
    """Get or create the singleton agent instance (lazy initialization)."""
    global _agent
    if _agent is None:
        _agent = build_agent()
    return _agent
