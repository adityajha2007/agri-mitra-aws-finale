"""Mandi (market) price query tool."""

import logging

from langchain_core.tools import tool

from app.services import dynamodb

logger = logging.getLogger(__name__)


@tool
def query_mandi_prices(crop_name: str, market: str = "", limit: int = 5) -> str:
    """Query current mandi (agricultural market) prices for a crop.

    Use this tool when the farmer asks about crop prices, market rates, or
    wants to compare prices across different mandis.

    Args:
        crop_name: Name of the crop (e.g., 'wheat', 'rice', 'tomato', 'onion')
        market: Optional market name to filter results (e.g., 'Azadpur', 'Vashi')
        limit: Maximum number of price records to return (default 5)

    Returns:
        Current mandi prices for the specified crop with market details
    """
    try:
        prices = dynamodb.query_mandi_prices(
            crop_name=crop_name.lower().strip(),
            market=market.strip() if market else None,
            limit=limit,
        )

        if not prices:
            return (
                f"No recent price data found for '{crop_name}'"
                + (f" at '{market}'" if market else "")
                + ". The crop name may be different in our records, or data may not be available yet."
            )

        lines = [f"**Mandi Prices for {crop_name.title()}** (latest {len(prices)} records):\n"]
        for p in prices:
            market_date = p.get("market_date", "")
            parts = market_date.split("#") if "#" in market_date else [market_date, ""]
            mkt = parts[0] if parts else "Unknown"
            date = parts[1] if len(parts) > 1 else ""

            lines.append(
                f"- **{p.get('market_name', mkt)}** ({p.get('state', 'N/A')}): "
                f"₹{p.get('price_per_quintal', 'N/A')}/quintal"
                + (f" | Date: {date}" if date else "")
                + (f" | Arrivals: {p.get('arrivals', 'N/A')} quintals" if p.get("arrivals") else "")
            )

        return "\n".join(lines)

    except Exception as e:
        logger.error("Mandi price query error: %s", e)
        return f"Error fetching mandi prices: {str(e)}"
