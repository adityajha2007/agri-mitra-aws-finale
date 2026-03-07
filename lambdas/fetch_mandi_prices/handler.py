"""Lambda: Fetch mandi prices from data.gov.in and store in DynamoDB.

Triggered every 6 hours by EventBridge cron rule.
"""

import json
import logging
import os
from datetime import datetime, timezone

import boto3
import urllib3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "agri-mitra-mandi-prices")
# data.gov.in API for daily mandi prices
DATA_GOV_API = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
API_KEY = os.environ.get("DATA_GOV_API_KEY", "")

http = urllib3.PoolManager()
dynamodb = boto3.resource("dynamodb")


def handler(event, context):
    """Fetch latest mandi prices and store in DynamoDB."""
    logger.info("Fetching mandi prices...")

    table = dynamodb.Table(DYNAMODB_TABLE)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    records_written = 0

    # Fetch prices for common crops
    crops = ["Wheat", "Rice", "Onion", "Tomato", "Potato", "Maize", "Cotton", "Soyabean"]

    for crop in crops:
        try:
            params = {
                "api-key": API_KEY,
                "format": "json",
                "limit": 50,
                "filters[commodity]": crop,
            }
            query = "&".join(f"{k}={v}" for k, v in params.items())
            url = f"{DATA_GOV_API}?{query}"

            response = http.request("GET", url, timeout=10.0)
            if response.status != 200:
                logger.warning("API returned %d for %s", response.status, crop)
                continue

            data = json.loads(response.data.decode("utf-8"))
            records = data.get("records", [])

            for record in records:
                item = {
                    "crop_name": crop.lower(),
                    "market_date": f"{record.get('market', 'Unknown')}#{record.get('arrival_date', today)}",
                    "market_name": record.get("market", "Unknown"),
                    "state": record.get("state", "Unknown"),
                    "price_per_quintal": int(record.get("modal_price", 0)),
                    "arrivals": int(record.get("arrivals_tonnes", 0)),
                    "min_price": int(record.get("min_price", 0)),
                    "max_price": int(record.get("max_price", 0)),
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                }
                table.put_item(Item=item)
                records_written += 1

        except Exception as e:
            logger.error("Error fetching prices for %s: %s", crop, e)
            continue

    logger.info("Wrote %d mandi price records", records_written)
    return {"statusCode": 200, "body": f"Wrote {records_written} price records"}
