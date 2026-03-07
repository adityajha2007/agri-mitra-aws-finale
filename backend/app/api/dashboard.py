"""Dashboard endpoints — serve cached data from DynamoDB."""

import logging

from fastapi import APIRouter, HTTPException, Query

from app.config import settings
from app.services import dynamodb

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/prices")
async def get_prices(
    crop: str = Query(default="", description="Filter by crop name"),
    limit: int = Query(default=20, ge=1, le=100),
):
    """Get cached mandi prices for the dashboard price ticker."""
    try:
        if crop:
            prices = dynamodb.query_mandi_prices(crop_name=crop.lower(), limit=limit)
        else:
            # Return a mix of common crops
            prices = []
            for c in ["wheat", "rice", "onion", "tomato", "potato"]:
                prices.extend(dynamodb.query_mandi_prices(crop_name=c, limit=4))
        return prices
    except Exception as e:
        logger.error("Dashboard prices error: %s", e)
        return []


@router.get("/weather")
async def get_weather(
    district: str = Query(default="Lucknow", description="District name"),
):
    """Get cached weather data for the dashboard weather widget."""
    try:
        weather = dynamodb.get_weather(district=district)
        if not weather:
            return {"district": district, "error": "No weather data available"}
        return weather
    except Exception as e:
        logger.error("Dashboard weather error: %s", e)
        return {"district": district, "error": str(e)}


@router.get("/news")
async def get_news(
    category: str = Query(default="", description="News category filter"),
    limit: int = Query(default=10, ge=1, le=50),
):
    """Get cached agricultural news for the dashboard news feed."""
    try:
        news = dynamodb.get_news(category=category or None, limit=limit)
        return news
    except Exception as e:
        logger.error("Dashboard news error: %s", e)
        return []


@router.get("/profile")
async def get_profile(
    farmer_id: str = Query(default="", description="Farmer ID"),
):
    """Get farmer profile for the dashboard."""
    fid = farmer_id or settings.default_farmer_id
    try:
        farmer = dynamodb.get_farmer(fid)
        if not farmer:
            return {
                "farmer_id": fid,
                "name": "Demo Farmer",
                "location": "Lucknow",
                "crops": ["wheat", "rice"],
                "land_acres": 5,
                "language": "hi",
            }
        return farmer
    except Exception as e:
        logger.error("Dashboard profile error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
