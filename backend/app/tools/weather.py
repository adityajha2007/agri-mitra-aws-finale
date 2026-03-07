"""Weather information tool."""

import logging

from langchain_core.tools import tool

from app.services import dynamodb

logger = logging.getLogger(__name__)


@tool
def get_weather(district: str) -> str:
    """Get current weather and agricultural advisory for a district.

    Use this tool when the farmer asks about weather conditions, forecasts,
    or needs weather-based farming advice (e.g., when to sow, irrigate, harvest).

    Args:
        district: District name (e.g., 'Pune', 'Lucknow', 'Varanasi')

    Returns:
        Weather information with agricultural advisory
    """
    try:
        weather = dynamodb.get_weather(district=district.strip())

        if not weather:
            return (
                f"No weather data available for '{district}'. "
                "Please check the district name or try a nearby district."
            )

        lines = [
            f"**Weather for {weather.get('district', district)}** ({weather.get('date', 'N/A')})\n",
            f"- Temperature: {weather.get('temperature_min', 'N/A')}°C - {weather.get('temperature_max', 'N/A')}°C",
            f"- Humidity: {weather.get('humidity', 'N/A')}%",
            f"- Rainfall: {weather.get('rainfall_mm', 0)} mm",
            f"- Wind Speed: {weather.get('wind_speed_kmh', 'N/A')} km/h",
            f"- Condition: {weather.get('description', 'N/A')}",
        ]

        advisory = weather.get("agricultural_advisory")
        if advisory:
            lines.append(f"\n**Agricultural Advisory**: {advisory}")

        return "\n".join(lines)

    except Exception as e:
        logger.error("Weather query error: %s", e)
        return f"Error fetching weather data: {str(e)}"
