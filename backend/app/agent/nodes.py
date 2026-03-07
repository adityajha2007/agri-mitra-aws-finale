"""Agent invocation helpers.

The actual ReAct nodes (reasoner, tool_executor, should_continue) are handled
internally by LangGraph's create_react_agent. This module provides helper
functions for invoking and streaming from the agent.
"""

from langchain_core.messages import HumanMessage

from app.agent.graph import get_agent


async def invoke_agent(
    message: str,
    farmer_id: str,
    image_key: str | None = None,
) -> dict:
    """Invoke the AgriMitra agent with a user message.

    Returns the full agent state including the response message and tools used.
    """
    content: list[dict] = [{"type": "text", "text": message}]

    if image_key:
        content.append({
            "type": "text",
            "text": f"[User uploaded a crop image: s3://{image_key}. Please analyze it.]",
        })

    config = {"configurable": {"thread_id": farmer_id}}

    agent = get_agent()
    result = await agent.ainvoke(
        {"messages": [HumanMessage(content=content)]},
        config=config,
    )

    last_message = result["messages"][-1]

    tools_used = []
    for msg in result["messages"]:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tools_used.append(tc["name"])

    return {
        "response": last_message.content,
        "tools_used": list(set(tools_used)),
        "farmer_id": farmer_id,
    }
