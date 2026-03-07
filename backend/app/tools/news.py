"""Agricultural news tool."""

import logging

from langchain_core.tools import tool

from app.services import dynamodb

logger = logging.getLogger(__name__)


@tool
def get_agri_news(category: str = "general", limit: int = 5) -> str:
    """Get recent agricultural news and updates.

    Use this tool when the farmer asks about agricultural news, policy updates,
    market trends, or farming-related current events.

    Args:
        category: News category — 'general', 'policy', 'market', 'technology', 'weather'
        limit: Maximum number of news items to return (default 5)

    Returns:
        Recent agricultural news articles with summaries
    """
    try:
        news_items = dynamodb.get_news(
            category=category.lower().strip() if category else None,
            limit=limit,
        )

        if not news_items:
            return f"No recent news available for category '{category}'. Try 'general' for all news."

        lines = [f"**Agricultural News** ({category.title()}):\n"]
        for item in news_items:
            lines.append(
                f"**{item.get('title', 'Untitled')}**\n"
                f"{item.get('summary', 'No summary available.')}\n"
                f"Source: {item.get('source_url', 'N/A')} | "
                f"Date: {item.get('timestamp', 'N/A')}"
            )
            tags = item.get("relevance_tags", [])
            if tags:
                lines.append(f"Tags: {', '.join(tags)}")
            lines.append("")

        return "\n".join(lines)

    except Exception as e:
        logger.error("News query error: %s", e)
        return f"Error fetching news: {str(e)}"
