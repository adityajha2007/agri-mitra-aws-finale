"""Tests for DynamoDB service wrapper using moto."""

import pytest
from moto import mock_aws

import app.services.dynamodb as db_service


@mock_aws
class TestFarmerOperations:
    def test_put_and_get_farmer(self, dynamodb_tables):
        # Reset the cached resource so moto's mock is used
        db_service._dynamodb_resource = None
        db_service._dynamodb_resource = dynamodb_tables

        farmer = {
            "farmer_id": "f-001",
            "name": "Raju",
            "location": "Lucknow",
            "crops": ["wheat", "rice"],
            "land_acres": 5,
            "language": "hi",
        }
        db_service.put_farmer(farmer)
        result = db_service.get_farmer("f-001")

        assert result is not None
        assert result["name"] == "Raju"
        assert result["crops"] == ["wheat", "rice"]
        assert result["land_acres"] == 5

    def test_get_nonexistent_farmer(self, dynamodb_tables):
        db_service._dynamodb_resource = dynamodb_tables
        result = db_service.get_farmer("nonexistent")
        assert result is None


@mock_aws
class TestMandiPriceOperations:
    def test_query_prices_by_crop(self, sample_mandi_prices):
        result = db_service.query_mandi_prices("wheat")
        assert len(result) == 2
        assert all(p["crop_name"] == "wheat" for p in result)

    def test_query_prices_by_market(self, sample_mandi_prices):
        result = db_service.query_mandi_prices("wheat", market="Azadpur")
        assert len(result) == 1
        assert result[0]["market_name"] == "Azadpur"

    def test_query_prices_empty(self, dynamodb_tables):
        db_service._dynamodb_resource = dynamodb_tables
        result = db_service.query_mandi_prices("dragonfruit")
        assert result == []


@mock_aws
class TestWeatherOperations:
    def test_get_latest_weather(self, sample_weather):
        result = db_service.get_weather("Lucknow")
        assert result is not None
        assert result["district"] == "Lucknow"
        assert result["temperature_max"] == 32

    def test_get_weather_nonexistent_district(self, dynamodb_tables):
        db_service._dynamodb_resource = dynamodb_tables
        result = db_service.get_weather("Atlantis")
        assert result is None


@mock_aws
class TestNewsOperations:
    def test_get_news_by_category(self, sample_news):
        result = db_service.get_news(category="general")
        assert len(result) == 1
        assert result[0]["title"] == "Wheat MSP increased for Rabi 2026"

    def test_get_all_news(self, sample_news):
        result = db_service.get_news()
        assert len(result) >= 1
