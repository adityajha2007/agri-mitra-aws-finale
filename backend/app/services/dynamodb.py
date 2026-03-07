"""AWS DynamoDB service wrapper for all table operations."""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key

from app.config import settings

logger = logging.getLogger(__name__)

_dynamodb_resource = None


def _get_resource():
    global _dynamodb_resource
    if _dynamodb_resource is None:
        _dynamodb_resource = boto3.resource(
            "dynamodb", region_name=settings.aws_region
        )
    return _dynamodb_resource


def _serialize(obj: Any) -> Any:
    """Convert floats to Decimal for DynamoDB compatibility."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize(v) for v in obj]
    return obj


def _deserialize(obj: Any) -> Any:
    """Convert Decimals back to float/int for JSON serialization."""
    if isinstance(obj, Decimal):
        if obj == int(obj):
            return int(obj)
        return float(obj)
    if isinstance(obj, dict):
        return {k: _deserialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_deserialize(v) for v in obj]
    return obj


# --- Farmer operations ---


def get_farmer(farmer_id: str) -> dict | None:
    table = _get_resource().Table(settings.dynamodb_table_farmers)
    resp = table.get_item(Key={"farmer_id": farmer_id})
    item = resp.get("Item")
    return _deserialize(item) if item else None


def put_farmer(farmer: dict) -> None:
    table = _get_resource().Table(settings.dynamodb_table_farmers)
    table.put_item(Item=_serialize(farmer))


# --- Conversation operations ---


def save_conversation(farmer_id: str, messages: list, tools_used: list) -> None:
    table = _get_resource().Table(settings.dynamodb_table_conversations)
    table.put_item(
        Item=_serialize(
            {
                "farmer_id": farmer_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "messages": messages,
                "tools_used": tools_used,
            }
        )
    )


def get_conversations(farmer_id: str, limit: int = 10) -> list[dict]:
    table = _get_resource().Table(settings.dynamodb_table_conversations)
    resp = table.query(
        KeyConditionExpression=Key("farmer_id").eq(farmer_id),
        ScanIndexForward=False,
        Limit=limit,
    )
    return [_deserialize(item) for item in resp.get("Items", [])]


# --- Mandi price operations ---


def query_mandi_prices(
    crop_name: str, market: str | None = None, limit: int = 10
) -> list[dict]:
    table = _get_resource().Table(settings.dynamodb_table_mandi_prices)

    if market:
        resp = table.query(
            KeyConditionExpression=Key("crop_name").eq(crop_name)
            & Key("market_date").begins_with(market),
            ScanIndexForward=False,
            Limit=limit,
        )
    else:
        resp = table.query(
            KeyConditionExpression=Key("crop_name").eq(crop_name),
            ScanIndexForward=False,
            Limit=limit,
        )
    return [_deserialize(item) for item in resp.get("Items", [])]


def put_mandi_price(price: dict) -> None:
    table = _get_resource().Table(settings.dynamodb_table_mandi_prices)
    table.put_item(Item=_serialize(price))


# --- Weather operations ---


def get_weather(district: str, date: str | None = None) -> dict | None:
    table = _get_resource().Table(settings.dynamodb_table_weather)
    if date:
        resp = table.get_item(Key={"district": district, "date": date})
    else:
        resp = table.query(
            KeyConditionExpression=Key("district").eq(district),
            ScanIndexForward=False,
            Limit=1,
        )
        items = resp.get("Items", [])
        return _deserialize(items[0]) if items else None
    item = resp.get("Item")
    return _deserialize(item) if item else None


def put_weather(weather: dict) -> None:
    table = _get_resource().Table(settings.dynamodb_table_weather)
    table.put_item(Item=_serialize(weather))


# --- News operations ---


def get_news(category: str | None = None, limit: int = 10) -> list[dict]:
    table = _get_resource().Table(settings.dynamodb_table_news)
    if category:
        resp = table.query(
            KeyConditionExpression=Key("category").eq(category),
            ScanIndexForward=False,
            Limit=limit,
        )
    else:
        resp = table.scan(Limit=limit)
    return [_deserialize(item) for item in resp.get("Items", [])]


def put_news(news_item: dict) -> None:
    table = _get_resource().Table(settings.dynamodb_table_news)
    table.put_item(Item=_serialize(news_item))


# --- Policy document operations ---


def get_policy_document(doc_id: str) -> dict | None:
    table = _get_resource().Table(settings.dynamodb_table_policy_docs)
    resp = table.get_item(Key={"doc_id": doc_id})
    item = resp.get("Item")
    return _deserialize(item) if item else None


def get_all_policy_documents() -> list[dict]:
    table = _get_resource().Table(settings.dynamodb_table_policy_docs)
    resp = table.scan()
    return [_deserialize(item) for item in resp.get("Items", [])]


def put_policy_document(doc: dict) -> None:
    table = _get_resource().Table(settings.dynamodb_table_policy_docs)
    table.put_item(Item=_serialize(doc))
