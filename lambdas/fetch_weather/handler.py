"""Lambda: Fetch weather data from OpenWeatherMap and store in DynamoDB.

Triggered every 3 hours by EventBridge cron rule.
"""

import json
import logging
import os
from datetime import datetime, timezone

import boto3
import urllib3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "agri-mitra-weather-cache")
OWM_API_KEY = os.environ.get("OPENWEATHERMAP_API_KEY", "")
OWM_BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

http = urllib3.PoolManager()
dynamodb = boto3.resource("dynamodb")

# Major agricultural districts in India (lat, lon)
DISTRICTS = {
    "Lucknow": (26.8467, 80.9462),
    "Pune": (18.5204, 73.8567),
    "Varanasi": (25.3176, 82.9739),
    "Jaipur": (26.9124, 75.7873),
    "Bhopal": (23.2599, 77.4126),
    "Nagpur": (21.1458, 79.0882),
    "Ludhiana": (30.9010, 75.8573),
    "Indore": (22.7196, 75.8577),
    "Patna": (25.6093, 85.1376),
    "Hyderabad": (17.3850, 78.4867),
}


def _generate_advisory(temp: float, humidity: float, rainfall: float) -> str:
    """Generate simple agricultural advisory based on weather conditions."""
    advisories = []

    if temp > 40:
        advisories.append("Extreme heat alert. Increase irrigation frequency. Provide shade for nursery plants.")
    elif temp > 35:
        advisories.append("High temperature. Ensure adequate irrigation during early morning or evening.")
    elif temp < 10:
        advisories.append("Cold conditions. Protect crops from frost using mulch or crop covers.")

    if rainfall > 50:
        advisories.append("Heavy rainfall expected. Ensure proper drainage. Delay fertilizer application.")
    elif rainfall > 10:
        advisories.append("Moderate rainfall. Good conditions for sowing. Reduce irrigation.")
    elif rainfall == 0 and humidity < 40:
        advisories.append("Dry conditions. Maintain regular irrigation schedule.")

    if humidity > 80:
        advisories.append("High humidity. Watch for fungal diseases. Consider preventive fungicide spray.")

    return " ".join(advisories) if advisories else "Normal weather conditions. Continue regular farming activities."


def handler(event, context):
    """Fetch weather data for agricultural districts and store in DynamoDB."""
    logger.info("Fetching weather data...")

    table = dynamodb.Table(DYNAMODB_TABLE)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    records_written = 0

    for district, (lat, lon) in DISTRICTS.items():
        try:
            url = f"{OWM_BASE_URL}?lat={lat}&lon={lon}&appid={OWM_API_KEY}&units=metric"
            response = http.request("GET", url, timeout=10.0)

            if response.status != 200:
                logger.warning("OWM returned %d for %s", response.status, district)
                continue

            data = json.loads(response.data.decode("utf-8"))
            main = data.get("main", {})
            wind = data.get("wind", {})
            weather = data.get("weather", [{}])[0]
            rain = data.get("rain", {})

            temp_min = main.get("temp_min", 0)
            temp_max = main.get("temp_max", 0)
            humidity = main.get("humidity", 0)
            rainfall = rain.get("1h", 0)

            item = {
                "district": district,
                "date": today,
                "temperature_min": int(temp_min),
                "temperature_max": int(temp_max),
                "humidity": int(humidity),
                "rainfall_mm": int(rainfall),
                "wind_speed_kmh": int(wind.get("speed", 0) * 3.6),
                "description": weather.get("description", "N/A"),
                "agricultural_advisory": _generate_advisory(temp_max, humidity, rainfall),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
            table.put_item(Item=item)
            records_written += 1

        except Exception as e:
            logger.error("Error fetching weather for %s: %s", district, e)
            continue

    logger.info("Wrote %d weather records", records_written)
    return {"statusCode": 200, "body": f"Wrote {records_written} weather records"}
