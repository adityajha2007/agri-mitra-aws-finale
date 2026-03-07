"""Tests for FastAPI endpoints."""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestHealthEndpoint:
    def test_health_check(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "agri-mitra"


class TestChatEndpoint:
    @patch("app.api.chat.invoke_agent", new_callable=AsyncMock)
    def test_chat_success(self, mock_agent):
        mock_agent.return_value = {
            "response": "Wheat price is ₹2,500/quintal at Azadpur mandi.",
            "tools_used": ["query_mandi_prices"],
            "farmer_id": "farmer-001",
        }

        response = client.post(
            "/api/chat",
            json={"message": "What is the price of wheat?"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "2,500" in data["response"]
        assert "query_mandi_prices" in data["tools_used"]

    def test_chat_empty_message(self):
        response = client.post(
            "/api/chat",
            json={"message": "   "},
        )
        assert response.status_code == 400

    @patch("app.api.chat.invoke_agent", new_callable=AsyncMock)
    def test_chat_with_image(self, mock_agent):
        mock_agent.return_value = {
            "response": "This appears to be leaf blight on wheat.",
            "tools_used": ["analyze_crop_image"],
            "farmer_id": "farmer-001",
        }

        response = client.post(
            "/api/chat",
            json={"message": "What disease is this?", "image_key": "uploads/test.jpg"},
        )
        assert response.status_code == 200
        assert "leaf blight" in response.json()["response"]


class TestDashboardEndpoints:
    @patch("app.api.dashboard.dynamodb")
    def test_get_prices(self, mock_db):
        mock_db.query_mandi_prices.return_value = [
            {
                "crop_name": "wheat",
                "market_name": "Azadpur",
                "price_per_quintal": 2500,
                "state": "Delhi",
            }
        ]
        response = client.get("/api/dashboard/prices?crop=wheat")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    @patch("app.api.dashboard.dynamodb")
    def test_get_weather(self, mock_db):
        mock_db.get_weather.return_value = {
            "district": "Lucknow",
            "date": "2026-03-04",
            "temperature_max": 32,
            "temperature_min": 18,
            "humidity": 65,
        }
        response = client.get("/api/dashboard/weather?district=Lucknow")
        assert response.status_code == 200
        data = response.json()
        assert data["district"] == "Lucknow"

    @patch("app.api.dashboard.dynamodb")
    def test_get_news(self, mock_db):
        mock_db.get_news.return_value = [
            {
                "title": "Test news",
                "summary": "Test summary",
                "category": "general",
                "timestamp": "2026-03-04T10:00:00Z",
            }
        ]
        response = client.get("/api/dashboard/news")
        assert response.status_code == 200
        assert len(response.json()) >= 1

    @patch("app.api.dashboard.dynamodb")
    def test_get_profile_default(self, mock_db):
        mock_db.get_farmer.return_value = None
        response = client.get("/api/dashboard/profile")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Demo Farmer"


class TestUploadEndpoint:
    @patch("app.api.upload.s3")
    def test_upload_image(self, mock_s3):
        mock_s3.upload_image.return_value = "uploads/test-uuid.jpg"

        response = client.post(
            "/api/upload",
            files={"file": ("test.jpg", b"fake-image-bytes", "image/jpeg")},
        )
        assert response.status_code == 200
        data = response.json()
        assert "s3_key" in data

    def test_upload_invalid_type(self):
        response = client.post(
            "/api/upload",
            files={"file": ("test.txt", b"not an image", "text/plain")},
        )
        assert response.status_code == 400
