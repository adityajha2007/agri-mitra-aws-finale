"""Shared test fixtures for AgriMitra backend tests."""

import os
import pytest
import boto3
from moto import mock_aws
from decimal import Decimal


@pytest.fixture(autouse=True)
def aws_env():
    """Set dummy AWS credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "ap-south-1"
    yield


@pytest.fixture
def dynamodb_tables():
    """Create all DynamoDB tables for testing using moto."""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="ap-south-1")

        # Farmers table
        dynamodb.create_table(
            TableName="agri-mitra-farmers",
            KeySchema=[{"AttributeName": "farmer_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "farmer_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        # Conversations table
        dynamodb.create_table(
            TableName="agri-mitra-conversations",
            KeySchema=[
                {"AttributeName": "farmer_id", "KeyType": "HASH"},
                {"AttributeName": "timestamp", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "farmer_id", "AttributeType": "S"},
                {"AttributeName": "timestamp", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        # Mandi prices table
        dynamodb.create_table(
            TableName="agri-mitra-mandi-prices",
            KeySchema=[
                {"AttributeName": "crop_name", "KeyType": "HASH"},
                {"AttributeName": "market_date", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "crop_name", "AttributeType": "S"},
                {"AttributeName": "market_date", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        # Weather table
        dynamodb.create_table(
            TableName="agri-mitra-weather-cache",
            KeySchema=[
                {"AttributeName": "district", "KeyType": "HASH"},
                {"AttributeName": "date", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "district", "AttributeType": "S"},
                {"AttributeName": "date", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        # News table
        dynamodb.create_table(
            TableName="agri-mitra-news",
            KeySchema=[
                {"AttributeName": "category", "KeyType": "HASH"},
                {"AttributeName": "timestamp", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "category", "AttributeType": "S"},
                {"AttributeName": "timestamp", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        # Policy documents table
        dynamodb.create_table(
            TableName="agri-mitra-policy-documents",
            KeySchema=[{"AttributeName": "doc_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "doc_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        yield dynamodb


@pytest.fixture
def s3_buckets():
    """Create S3 buckets for testing using moto."""
    with mock_aws():
        s3 = boto3.client("s3", region_name="ap-south-1")
        s3.create_bucket(
            Bucket="agri-mitra-policies",
            CreateBucketConfiguration={"LocationConstraint": "ap-south-1"},
        )
        s3.create_bucket(
            Bucket="agri-mitra-uploads",
            CreateBucketConfiguration={"LocationConstraint": "ap-south-1"},
        )
        yield s3


@pytest.fixture
def sample_mandi_prices(dynamodb_tables):
    """Seed mandi_prices table with sample data."""
    table = dynamodb_tables.Table("agri-mitra-mandi-prices")
    prices = [
        {
            "crop_name": "wheat",
            "market_date": "Azadpur#2026-03-04",
            "market_name": "Azadpur",
            "state": "Delhi",
            "price_per_quintal": 2500,
            "arrivals": 100,
        },
        {
            "crop_name": "wheat",
            "market_date": "Vashi#2026-03-04",
            "market_name": "Vashi",
            "state": "Maharashtra",
            "price_per_quintal": 2600,
            "arrivals": 80,
        },
        {
            "crop_name": "rice",
            "market_date": "Azadpur#2026-03-04",
            "market_name": "Azadpur",
            "state": "Delhi",
            "price_per_quintal": 3500,
            "arrivals": 60,
        },
    ]
    for p in prices:
        table.put_item(Item=p)
    return prices


@pytest.fixture
def sample_weather(dynamodb_tables):
    """Seed weather_cache table with sample data."""
    table = dynamodb_tables.Table("agri-mitra-weather-cache")
    weather = {
        "district": "Lucknow",
        "date": "2026-03-04",
        "temperature_min": 18,
        "temperature_max": 32,
        "humidity": 65,
        "rainfall_mm": 0,
        "wind_speed_kmh": 12,
        "description": "Clear sky",
        "agricultural_advisory": "Normal weather. Continue regular farming activities.",
    }
    table.put_item(Item=weather)
    return weather


@pytest.fixture
def sample_news(dynamodb_tables):
    """Seed news table with sample data."""
    table = dynamodb_tables.Table("agri-mitra-news")
    news_items = [
        {
            "category": "general",
            "timestamp": "2026-03-04T10:00:00Z",
            "title": "Wheat MSP increased for Rabi 2026",
            "summary": "Government announces increase in MSP for wheat.",
            "source_url": "https://example.com/1",
            "relevance_tags": ["wheat", "msp"],
        },
        {
            "category": "market",
            "timestamp": "2026-03-04T08:00:00Z",
            "title": "Onion prices surge in Maharashtra",
            "summary": "Onion prices rise due to supply shortage.",
            "source_url": "https://example.com/2",
            "relevance_tags": ["onion"],
        },
    ]
    for item in news_items:
        table.put_item(Item=item)
    return news_items
