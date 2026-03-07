"""Lambda: Fetch agricultural news and store in DynamoDB.

Triggered every 12 hours by EventBridge cron rule.
"""

import json
import logging
import os
from datetime import datetime, timezone

import boto3
import urllib3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "agri-mitra-news")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "")
NEWS_API_URL = "https://newsapi.org/v2/everything"

http = urllib3.PoolManager()
dynamodb = boto3.resource("dynamodb")

# Search queries for different agricultural news categories
CATEGORIES = {
    "general": "India agriculture farming",
    "policy": "India agricultural policy government scheme",
    "market": "India mandi crop prices market",
    "technology": "India agritech farming technology",
    "weather": "India monsoon drought agriculture weather",
}


def _extract_tags(title: str, description: str) -> list[str]:
    """Extract relevance tags from article content."""
    text = f"{title} {description}".lower()
    tags = []
    keywords = {
        "wheat": "wheat", "rice": "rice", "cotton": "cotton",
        "msp": "msp", "subsidy": "subsidy", "monsoon": "monsoon",
        "kisan": "kisan", "irrigation": "irrigation", "organic": "organic",
        "fertilizer": "fertilizer", "pesticide": "pesticide",
    }
    for keyword, tag in keywords.items():
        if keyword in text:
            tags.append(tag)
    return tags[:5]


def handler(event, context):
    """Fetch agricultural news and store in DynamoDB."""
    logger.info("Fetching agricultural news...")

    table = dynamodb.Table(DYNAMODB_TABLE)
    records_written = 0

    for category, query in CATEGORIES.items():
        try:
            params = {
                "q": query,
                "apiKey": NEWS_API_KEY,
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": "10",
            }
            query_str = "&".join(f"{k}={v}" for k, v in params.items())
            url = f"{NEWS_API_URL}?{query_str}"

            response = http.request("GET", url, timeout=10.0)
            if response.status != 200:
                logger.warning("News API returned %d for %s", response.status, category)
                continue

            data = json.loads(response.data.decode("utf-8"))
            articles = data.get("articles", [])

            for article in articles:
                title = article.get("title", "")
                description = article.get("description", "")

                if not title:
                    continue

                item = {
                    "category": category,
                    "timestamp": article.get("publishedAt", datetime.now(timezone.utc).isoformat()),
                    "title": title,
                    "summary": description or "No summary available.",
                    "source_url": article.get("url", ""),
                    "source_name": article.get("source", {}).get("name", "Unknown"),
                    "relevance_tags": _extract_tags(title, description),
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                }
                table.put_item(Item=item)
                records_written += 1

        except Exception as e:
            logger.error("Error fetching news for %s: %s", category, e)
            continue

    logger.info("Wrote %d news records", records_written)
    return {"statusCode": 200, "body": f"Wrote {records_written} news records"}
