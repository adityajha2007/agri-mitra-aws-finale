"""
Agri-Mitra Lambda Handler
=========================
Self-contained Lambda handler for API Gateway v2 (HTTP API).
Routes all requests and implements a ReAct agent using Bedrock Converse API.

No local imports — only stdlib + boto3 (available in Lambda runtime).
"""

# ==============================================================================
# 1. SETUP & HELPERS
# ==============================================================================

import json
import os
import math
import re
import base64
import boto3
from decimal import Decimal
from datetime import datetime
from boto3.dynamodb.conditions import Key

REGION = "ap-south-1"
dynamodb = boto3.resource("dynamodb", region_name=REGION)
s3 = boto3.client("s3", region_name=REGION)
bedrock = boto3.client("bedrock-runtime", region_name=REGION)

# Table names from env vars with defaults
MANDI_PRICES_TABLE = os.environ.get("AGRI_MITRA_DYNAMODB_TABLE_MANDI_PRICES", "agri-mitra-mandi-prices")
WEATHER_TABLE = os.environ.get("AGRI_MITRA_DYNAMODB_TABLE_WEATHER", "agri-mitra-weather-cache")
NEWS_TABLE = os.environ.get("AGRI_MITRA_DYNAMODB_TABLE_NEWS", "agri-mitra-news")
POLICY_DOCS_TABLE = os.environ.get("AGRI_MITRA_DYNAMODB_TABLE_POLICY_DOCS", "agri-mitra-policy-documents")
FARMERS_TABLE = os.environ.get("AGRI_MITRA_DYNAMODB_TABLE_FARMERS", "agri-mitra-farmers")
CONVERSATIONS_TABLE = os.environ.get("AGRI_MITRA_DYNAMODB_TABLE_CONVERSATIONS", "agri-mitra-conversations")
POLICIES_BUCKET = os.environ.get("AGRI_MITRA_S3_BUCKET_POLICIES", "")
UPLOADS_BUCKET = os.environ.get("AGRI_MITRA_S3_BUCKET_UPLOADS", "")

# MODEL_ID = "apac.amazon.nova-lite-v1:0"

# Using Intelligent Prompt Routing
MODEL_ID = "arn:aws:bedrock:ap-south-1:415197220733:default-prompt-router/amazon.nova:1"
EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v2:0"


def decimal_to_native(obj):
    """Recursively convert Decimal objects to int/float for JSON serialization."""
    if isinstance(obj, Decimal):
        return int(obj) if obj == int(obj) else float(obj)
    if isinstance(obj, dict):
        return {k: decimal_to_native(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [decimal_to_native(i) for i in obj]
    return obj


def api_response(status_code, body):
    """Build a standard API Gateway v2 response with CORS headers."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        },
        "body": json.dumps(decimal_to_native(body), default=str),
    }


# ==============================================================================
# 2. ROUTER (main handler)
# ==============================================================================

def handler(event, context):
    """Main Lambda entry point — routes all API Gateway v2 requests."""
    print(f"Event: {json.dumps(event)}")

    http_method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    path = event.get("rawPath", "/")

    # CORS preflight
    if http_method == "OPTIONS":
        return api_response(200, {"message": "OK"})

    # Route
    if path == "/health":
        return health_check()
    elif path == "/api/dashboard/prices":
        return get_dashboard_prices(event)
    elif path == "/api/dashboard/weather":
        return get_dashboard_weather(event)
    elif path == "/api/dashboard/news":
        return get_dashboard_news(event)
    elif path == "/api/chat" and http_method == "POST":
        return handle_chat(event)
    elif path == "/api/upload" and http_method == "POST":
        return handle_upload(event)
    elif path == "/sms" and http_method == "POST":
        return handle_twilio_webhook(event)
    else:
        return api_response(404, {"error": "Not found", "path": path})


# ==============================================================================
# 3. HEALTH CHECK
# ==============================================================================

def health_check():
    """Return service health status."""
    return api_response(200, {
        "status": "healthy",
        "service": "agri-mitra-backend",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0-lambda",
    })


# ==============================================================================
# 4. DASHBOARD ENDPOINTS
# ==============================================================================

def get_dashboard_prices(event):
    """GET /api/dashboard/prices — query mandi prices from DynamoDB."""
    try:
        params = event.get("queryStringParameters", {}) or {}
        crop = params.get("crop")
        table = dynamodb.Table(MANDI_PRICES_TABLE)

        if crop:
            response = table.query(
                KeyConditionExpression=Key("crop_name").eq(crop)
            )
        else:
            response = table.scan(Limit=60)

        items = response.get("Items", [])

        # Transform: extract date from sort key "MarketName#2026-03-06"
        results = []
        for item in items:
            market_date_raw = item.get("market_date", "")
            parts = market_date_raw.split("#")
            date_val = parts[1] if len(parts) > 1 else market_date_raw

            results.append({
                "crop_name": item.get("crop_name", ""),
                "market_name": item.get("market_name", parts[0] if parts else ""),
                "price_per_quintal": item.get("price_per_quintal", 0),
                "date": date_val,
                "state": item.get("state", ""),
                "arrivals": item.get("arrivals", 0),
            })

        return api_response(200, results)

    except Exception as e:
        print(f"Error getting mandi prices: {e}")
        return api_response(500, {"error": f"Failed to fetch prices: {str(e)}"})


def get_dashboard_weather(event):
    """GET /api/dashboard/weather — get latest weather for a district."""
    try:
        params = event.get("queryStringParameters", {}) or {}
        district = params.get("district", "Lucknow")
        table = dynamodb.Table(WEATHER_TABLE)

        response = table.query(
            KeyConditionExpression=Key("district").eq(district),
            ScanIndexForward=False,
            Limit=1,
        )

        items = response.get("Items", [])
        if not items:
            return api_response(404, {
                "error": f"No weather data found for district: {district}"
            })

        item = items[0]
        return api_response(200, {
            "district": item.get("district", district),
            "date": item.get("date", ""),
            "temperature_min": item.get("temperature_min", 0),
            "temperature_max": item.get("temperature_max", 0),
            "humidity": item.get("humidity", 0),
            "rainfall_mm": item.get("rainfall_mm", 0),
            "description": item.get("description", ""),
            "agricultural_advisory": item.get("agricultural_advisory", ""),
        })

    except Exception as e:
        print(f"Error getting weather: {e}")
        return api_response(500, {"error": f"Failed to fetch weather: {str(e)}"})


def get_dashboard_news(event):
    """GET /api/dashboard/news — get latest agricultural news."""
    try:
        params = event.get("queryStringParameters", {}) or {}
        category = params.get("category")
        limit = int(params.get("limit", "20"))
        table = dynamodb.Table(NEWS_TABLE)

        if category:
            response = table.query(
                KeyConditionExpression=Key("category").eq(category),
                ScanIndexForward=False,
                Limit=limit,
            )
        else:
            response = table.scan(Limit=limit)

        items = response.get("Items", [])

        results = []
        for item in items:
            results.append({
                "title": item.get("title", ""),
                "summary": item.get("summary", ""),
                "source_url": item.get("source_url", ""),
                "category": item.get("category", ""),
                "timestamp": item.get("timestamp", ""),
                "relevance_tags": item.get("relevance_tags", []),
            })

        return api_response(200, results)

    except Exception as e:
        print(f"Error getting news: {e}")
        return api_response(500, {"error": f"Failed to fetch news: {str(e)}"})


# ==============================================================================
# 5. REACT AGENT — SYSTEM PROMPT & TOOL DEFINITIONS
# ==============================================================================

SYSTEM_PROMPT = """You are Agri-Mitra, an AI agricultural assistant for Indian farmers. You help with:
- Crop market prices (mandi prices)
- Weather forecasts and farming advisories
- Government agricultural policies and schemes
- Crop disease diagnosis from images
- Agricultural calculations (yield, profit, costs)
- Latest farming news

IMPORTANT RULES:
1. Always use tools to fetch real data. NEVER fabricate prices, weather, or policy information.
2. When a farmer asks about prices, call get_mandi_prices. For weather, call get_weather. For news, call get_news.
3. Present information clearly with practical, actionable advice.
4. Be respectful and supportive. Many users are small-scale Indian farmers.
5. If a calculation is needed, use the calculate tool rather than doing math yourself.
6. For policy/scheme questions, use search_policies to find relevant government programs.
7. Keep responses concise but informative.
8. NEVER use XML tags like <thinking>, <response>, or any other XML markup in your responses. Just respond with plain text directly.
9. Do NOT wrap your reasoning or output in any tags. Give your answer directly.

CRITICAL LANGUAGE RULE:
You MUST always reply in the SAME language the user is using. If the user writes in Hindi, reply in Hindi. If in English, reply in English. If in Marathi, reply in Marathi. Match the user's language exactly."""

TOOL_DEFINITIONS = [
    {
        "toolSpec": {
            "name": "get_mandi_prices",
            "description": "Get current mandi (market) prices for agricultural crops. Use when user asks about crop prices, market rates, or mandi information.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "crop_name": {
                            "type": "string",
                            "description": "Name of the crop (e.g. wheat, rice, onion, tomato)"
                        },
                        "market_name": {
                            "type": "string",
                            "description": "Optional market/mandi name to filter results"
                        }
                    },
                    "required": ["crop_name"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "get_weather",
            "description": "Get current weather data and agricultural advisory for a district. Use when user asks about weather, temperature, rainfall, or farming conditions.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "district": {
                            "type": "string",
                            "description": "District name (e.g. Lucknow, Mumbai, Pune)"
                        }
                    },
                    "required": ["district"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "get_news",
            "description": "Get latest agricultural news articles. Use when user asks about farming news, government schemes, policy updates.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "enum": ["policy", "market", "technology", "weather", "general"],
                            "description": "News category to filter by"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of articles to return"
                        }
                    },
                    "required": []
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "calculate",
            "description": "Perform agricultural calculations: yield estimation, profit, costs, market comparison.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "operation": {
                            "type": "string",
                            "enum": ["yield", "profit", "cost", "best_market"],
                            "description": "Type of calculation to perform"
                        },
                        "crop_name": {
                            "type": "string",
                            "description": "Crop name for yield estimation"
                        },
                        "land_acres": {
                            "type": "number",
                            "description": "Land area in acres"
                        },
                        "price_per_quintal": {
                            "type": "number",
                            "description": "Price per quintal in INR"
                        },
                        "costs": {
                            "type": "number",
                            "description": "Total costs in INR"
                        },
                        "markets": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "price": {"type": "number"}
                                }
                            },
                            "description": "List of markets with prices for comparison"
                        }
                    },
                    "required": ["operation"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "search_policies",
            "description": "Search government agricultural policies and schemes using semantic search. Use for subsidies, schemes, insurance, loans questions.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query describing the policy or scheme"
                        },
                        "state": {
                            "type": "string",
                            "description": "Optional state name to narrow results"
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "analyze_crop_image",
            "description": "Analyze a crop image for disease detection, pest identification, health assessment.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "image_key": {
                            "type": "string",
                            "description": "S3 key of the uploaded crop image"
                        }
                    },
                    "required": ["image_key"]
                }
            }
        }
    },
]


# ==============================================================================
# 6. TOOL EXECUTION FUNCTIONS
# ==============================================================================

def tool_get_mandi_prices(params):
    """Query DynamoDB mandi_prices table by crop_name."""
    try:
        crop_name = params.get("crop_name", "")
        market_name_filter = params.get("market_name")
        table = dynamodb.Table(MANDI_PRICES_TABLE)

        response = table.query(
            KeyConditionExpression=Key("crop_name").eq(crop_name)
        )
        items = response.get("Items", [])

        if not items:
            return f"No price data found for crop: {crop_name}"

        # Filter by market name if provided
        if market_name_filter:
            items = [
                i for i in items
                if market_name_filter.lower() in i.get("market_name", "").lower()
                or market_name_filter.lower() in i.get("market_date", "").lower()
            ]
            if not items:
                return f"No price data found for {crop_name} at market: {market_name_filter}"

        # Format results
        lines = [f"Mandi prices for {crop_name}:"]
        for item in items:
            market_date_raw = item.get("market_date", "")
            parts = market_date_raw.split("#")
            market = parts[0] if parts else "Unknown"
            date_val = parts[1] if len(parts) > 1 else market_date_raw
            price = decimal_to_native(item.get("price_per_quintal", 0))
            state = item.get("state", "")
            arrivals = decimal_to_native(item.get("arrivals", 0))
            lines.append(
                f"  - {market} ({state}): Rs {price}/quintal on {date_val} (arrivals: {arrivals} quintals)"
            )

        return "\n".join(lines)

    except Exception as e:
        return f"Error fetching mandi prices: {str(e)}"


def tool_get_weather(params):
    """Query DynamoDB weather table by district, get latest entry."""
    try:
        district = params.get("district", "Lucknow")
        table = dynamodb.Table(WEATHER_TABLE)

        response = table.query(
            KeyConditionExpression=Key("district").eq(district),
            ScanIndexForward=False,
            Limit=1,
        )
        items = response.get("Items", [])

        if not items:
            return f"No weather data found for district: {district}"

        item = items[0]
        temp_min = decimal_to_native(item.get("temperature_min", 0))
        temp_max = decimal_to_native(item.get("temperature_max", 0))
        humidity = decimal_to_native(item.get("humidity", 0))
        rainfall = decimal_to_native(item.get("rainfall_mm", 0))
        description = item.get("description", "N/A")
        advisory = item.get("agricultural_advisory", "N/A")
        date_val = item.get("date", "")

        return (
            f"Weather for {district} ({date_val}):\n"
            f"  Temperature: {temp_min}C - {temp_max}C\n"
            f"  Humidity: {humidity}%\n"
            f"  Rainfall: {rainfall} mm\n"
            f"  Conditions: {description}\n"
            f"  Agricultural Advisory: {advisory}"
        )

    except Exception as e:
        return f"Error fetching weather: {str(e)}"


def tool_get_news(params):
    """Query/scan DynamoDB news table."""
    try:
        category = params.get("category")
        limit = int(params.get("limit", 10))
        table = dynamodb.Table(NEWS_TABLE)

        if category:
            response = table.query(
                KeyConditionExpression=Key("category").eq(category),
                ScanIndexForward=False,
                Limit=limit,
            )
        else:
            response = table.scan(Limit=limit)

        items = response.get("Items", [])

        if not items:
            cat_msg = f" in category '{category}'" if category else ""
            return f"No news articles found{cat_msg}."

        lines = ["Latest agricultural news:"]
        for item in items:
            title = item.get("title", "Untitled")
            summary = item.get("summary", "")
            source = item.get("source_url", "")
            ts = item.get("timestamp", "")
            lines.append(f"  - [{ts}] {title}")
            if summary:
                lines.append(f"    {summary}")
            if source:
                lines.append(f"    Source: {source}")

        return "\n".join(lines)

    except Exception as e:
        return f"Error fetching news: {str(e)}"


# Average yield per acre in quintals
YIELD_DATA = {
    "wheat": 20,
    "rice": 25,
    "onion": 100,
    "tomato": 80,
    "potato": 100,
    "maize": 30,
    "cotton": 8,
    "soyabean": 12,
    "mustard": 8,
    "sugarcane": 350,
}


def tool_calculate(params):
    """Deterministic agricultural calculations."""
    try:
        operation = params.get("operation", "")
        crop_name = (params.get("crop_name") or "").lower()
        land_acres = float(params.get("land_acres", 0))
        price_per_quintal = float(params.get("price_per_quintal", 0))
        costs = float(params.get("costs", 0))
        markets = params.get("markets", [])

        if operation == "yield":
            avg_yield = YIELD_DATA.get(crop_name)
            if avg_yield is None:
                available = ", ".join(sorted(YIELD_DATA.keys()))
                return (
                    f"No yield data for '{crop_name}'. "
                    f"Available crops: {available}"
                )
            estimated = land_acres * avg_yield
            return (
                f"Yield Estimate for {crop_name}:\n"
                f"  Average yield: {avg_yield} quintals/acre\n"
                f"  Land: {land_acres} acres\n"
                f"  Estimated total yield: {estimated:.1f} quintals"
            )

        elif operation == "profit":
            avg_yield = YIELD_DATA.get(crop_name, 0)
            total_yield = land_acres * avg_yield if (land_acres and avg_yield) else 0
            revenue = total_yield * price_per_quintal
            profit = revenue - costs
            return (
                f"Profit Estimate for {crop_name}:\n"
                f"  Estimated yield: {total_yield:.1f} quintals\n"
                f"  Revenue (yield x price): Rs {revenue:,.0f}\n"
                f"  Costs: Rs {costs:,.0f}\n"
                f"  Net Profit: Rs {profit:,.0f}"
            )

        elif operation == "cost":
            if land_acres <= 0:
                return "Land area must be greater than 0 for cost calculation."
            cost_per_acre = costs / land_acres
            return (
                f"Cost Analysis:\n"
                f"  Total costs: Rs {costs:,.0f}\n"
                f"  Land: {land_acres} acres\n"
                f"  Cost per acre: Rs {cost_per_acre:,.0f}"
            )

        elif operation == "best_market":
            if not markets:
                return "No markets provided for comparison."
            best = max(markets, key=lambda m: float(m.get("price", 0)))
            lines = ["Market Comparison:"]
            for m in markets:
                marker = " <-- BEST" if m.get("name") == best.get("name") else ""
                lines.append(f"  - {m.get('name', 'Unknown')}: Rs {m.get('price', 0)}/quintal{marker}")
            lines.append(f"\nRecommendation: Sell at {best.get('name')} for Rs {best.get('price')}/quintal")
            return "\n".join(lines)

        else:
            return f"Unknown operation: {operation}. Supported: yield, profit, cost, best_market"

    except Exception as e:
        return f"Calculation error: {str(e)}"


def cosine_similarity(vec_a, vec_b):
    """Compute cosine similarity between two vectors."""
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    mag_a = math.sqrt(sum(a * a for a in vec_a))
    mag_b = math.sqrt(sum(b * b for b in vec_b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def tool_search_policies(params):
    """Semantic search over government policy documents using embeddings."""
    try:
        query = params.get("query", "")
        state_filter = params.get("state")

        # 1. Generate query embedding via Bedrock Titan Embed v2
        embed_response = bedrock.invoke_model(
            modelId=EMBEDDING_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps({"inputText": query}),
        )
        embed_body = json.loads(embed_response["body"].read())
        query_embedding = embed_body.get("embedding", [])

        if not query_embedding:
            return "Failed to generate embedding for the query."

        # 2. Scan policy_docs table
        table = dynamodb.Table(POLICY_DOCS_TABLE)
        response = table.scan()
        items = response.get("Items", [])

        if not items:
            return "No policy documents found in the database."

        # 3. Compute cosine similarity
        scored = []
        for item in items:
            stored_embedding = item.get("embedding", [])
            if stored_embedding:
                # Convert Decimal list to float
                stored_embedding = [float(x) for x in stored_embedding]
                sim = cosine_similarity(query_embedding, stored_embedding)
            else:
                sim = 0.0

            # Optional state filter
            if state_filter:
                item_state = (item.get("state", "") or "").lower()
                if state_filter.lower() not in item_state and item_state != "":
                    continue

            scored.append((sim, item))

        # 4. Sort by similarity, take top 3
        scored.sort(key=lambda x: x[0], reverse=True)
        top_matches = scored[:3]

        if not top_matches:
            return f"No matching policies found for: {query}"

        lines = [f"Top policy matches for '{query}':"]
        for rank, (sim, item) in enumerate(top_matches, 1):
            doc_id = item.get("doc_id", "unknown")
            title = item.get("title", "Untitled Policy")
            description = item.get("description", "")
            s3_key = item.get("s3_key", "")

            lines.append(f"\n{rank}. {title} (relevance: {sim:.2f})")
            if description:
                lines.append(f"   {description}")

            # Fetch policy text from S3 if available
            if s3_key and POLICIES_BUCKET:
                try:
                    s3_obj = s3.get_object(Bucket=POLICIES_BUCKET, Key=s3_key)
                    policy_text = s3_obj["Body"].read().decode("utf-8")
                    # Truncate to first 1000 chars
                    if len(policy_text) > 1000:
                        policy_text = policy_text[:1000] + "..."
                    lines.append(f"   Content: {policy_text}")
                except Exception as s3_err:
                    lines.append(f"   (Could not fetch full document: {s3_err})")

        return "\n".join(lines)

    except Exception as e:
        return f"Error searching policies: {str(e)}"


def tool_analyze_crop_image(params):
    """Download crop image from S3 and analyze it using Bedrock Vision."""
    try:
        image_key = params.get("image_key", "")

        if not image_key:
            return "No image key provided."
        if not UPLOADS_BUCKET:
            return "Uploads bucket not configured."

        # 1. Download image from S3
        try:
            s3_obj = s3.get_object(Bucket=UPLOADS_BUCKET, Key=image_key)
            image_bytes = s3_obj["Body"].read()
        except Exception as s3_err:
            return f"Failed to download image from S3: {str(s3_err)}"

        # 2. Determine image format from extension
        ext = image_key.rsplit(".", 1)[-1].lower() if "." in image_key else "jpeg"
        format_map = {
            "jpg": "jpeg",
            "jpeg": "jpeg",
            "png": "png",
            "gif": "gif",
            "webp": "webp",
        }
        image_format = format_map.get(ext, "jpeg")

        # 3. Call Bedrock Converse with image for crop diagnosis
        VISION_MODEL_ID = "apac.amazon.nova-lite-v1:0"
        analysis_response = bedrock.converse(
            modelId=VISION_MODEL_ID,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "image": {
                                "format": image_format,
                                "source": {"bytes": image_bytes},
                            }
                        },
                        {
                            "text": (
                                "You are an expert agricultural scientist. Analyze this image and provide the following information if the attached image is of a crop:\n"
                                "1. Crop identification (if possible)\n"
                                "2. Health assessment (healthy/diseased/stressed)\n"
                                "3. Disease or pest identification (if any)\n"
                                "4. Severity level (mild/moderate/severe)\n"
                                "5. Recommended treatment or action\n"
                                "6. Preventive measures\n"
                                "NOTE: Be specific and practical in your recommendations. If the image is not of a crop or plant, politely say so."
                            )
                        },
                    ],
                }
            ],
            inferenceConfig={"maxTokens": 1024, "temperature": 0.2},
        )

        # Extract text from response
        output_msg = analysis_response["output"]["message"]
        result_text = ""
        for block in output_msg["content"]:
            if "text" in block:
                result_text += block["text"]

        return result_text if result_text else "Image analysis returned no results."

    except Exception as e:
        return f"Error analyzing crop image: {str(e)}"


# Tool dispatch map
TOOL_DISPATCH = {
    "get_mandi_prices": tool_get_mandi_prices,
    "get_weather": tool_get_weather,
    "get_news": tool_get_news,
    "calculate": tool_calculate,
    "search_policies": tool_search_policies,
    "analyze_crop_image": tool_analyze_crop_image,
}


# ==============================================================================
# 7. IMAGE UPLOAD (handle_upload)
# ==============================================================================

def handle_upload(event):
    """Handle POST /api/upload — upload a crop image to S3."""
    try:
        if not UPLOADS_BUCKET:
            return api_response(500, {"error": "Uploads bucket not configured"})

        content_type = event.get("headers", {}).get("content-type", "")
        body = event.get("body", "")
        is_base64 = event.get("isBase64Encoded", False)

        if is_base64:
            body_bytes = base64.b64decode(body)
        else:
            body_bytes = body.encode("utf-8") if isinstance(body, str) else body

        # Parse multipart form data to extract file
        if "multipart/form-data" in content_type:
            # Extract boundary — handle possible quotes and extra params
            boundary = None
            for part in content_type.split(";"):
                part = part.strip()
                if part.startswith("boundary="):
                    boundary = part[len("boundary="):].strip().strip('"')
                    break

            if not boundary:
                return api_response(400, {"error": "Missing multipart boundary"})

            boundary_bytes = f"--{boundary}".encode()
            parts = body_bytes.split(boundary_bytes)

            file_data = None
            filename = "upload.jpg"

            for part in parts:
                if b"Content-Disposition" not in part or b"filename=" not in part:
                    continue

                # Split headers from body at double CRLF
                header_end = part.find(b"\r\n\r\n")
                if header_end == -1:
                    continue

                header_str = part[:header_end].decode("utf-8", errors="ignore")
                file_content = part[header_end + 4:]

                # Extract filename from Content-Disposition header
                for line in header_str.split("\r\n"):
                    if "filename=" in line:
                        match = re.search(r'filename="([^"]+)"', line)
                        if match:
                            filename = match.group(1)

                # Remove trailing CRLF and boundary closing
                if file_content.endswith(b"--\r\n"):
                    file_content = file_content[:-4]
                elif file_content.endswith(b"--"):
                    file_content = file_content[:-2]
                file_data = file_content.rstrip(b"\r\n")
                break

            if not file_data:
                return api_response(400, {"error": "No file found in upload"})
        else:
            file_data = body_bytes
            filename = "upload.jpg"

        # Generate unique S3 key
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
        safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
        s3_key = f"crops/{timestamp}_{safe_name}"

        # Determine content type
        mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                    "gif": "image/gif", "webp": "image/webp"}
        mime_type = mime_map.get(ext, "image/jpeg")

        # Upload to S3
        s3.put_object(
            Bucket=UPLOADS_BUCKET,
            Key=s3_key,
            Body=file_data,
            ContentType=mime_type,
        )

        return api_response(200, {
            "s3_key": s3_key,
            "filename": filename,
        })

    except Exception as e:
        print(f"Upload error: {e}")
        return api_response(500, {"error": f"Upload failed: {str(e)}"})


# ==============================================================================
# 8. REACT AGENT (handle_chat)
# ==============================================================================

def handle_chat(event):
    """Handle POST /api/chat — ReAct agent loop using Bedrock Converse API."""
    try:
        body = json.loads(event.get("body", "{}"))
        message = body.get("message", "")
        farmer_id = body.get("farmer_id", "anonymous")
        image_key = body.get("image_key")

        if not message and not image_key:
            return api_response(400, {"error": "Message or image required"})

        # Build conversation history from client
        history = body.get("history", [])
        messages = []
        BLOCKED_MESSAGE = "Sorry, AgriMitra cannot answer this. This seems to be an harmful or blocked request-response. Please try again with a different query"
        latest_message_was_blocked = False
        for h in history[::-1]:  # Last 10 messages for context window safety
            if latest_message_was_blocked:
                latest_message_was_blocked = False
                continue
            
            role = h.get("role", "user")
            content = h.get("content", "")
            if role in ("user", "assistant") and content:
                if content == BLOCKED_MESSAGE:
                    latest_message_was_blocked = True
                else:
                    messages.append({"role": role, "content": [{"text": content}]})
                    if len(messages) >= 10:
                        break
        
        messages = messages[::-1]

        # Add current user message
        if image_key:
            user_text = f"{message or 'Please analyze this crop image.'}\n\n[User uploaded a crop image with key: {image_key}. Use the analyze_crop_image tool with this image_key to analyze it.]"
        else:
            user_text = message
        user_content = [{"text": user_text}]
        latest_message = {"role": "user", "content": user_content}
        tools_used = []

        # ReAct loop — up to 5 iterations
        for iteration in range(5):
            response = bedrock.converse(
                modelId=MODEL_ID,
                system=[{"text": SYSTEM_PROMPT}],
                messages=messages + [latest_message],
                toolConfig={"tools": TOOL_DEFINITIONS},
                inferenceConfig={"maxTokens": 2048, "temperature": 0.3},
                guardrailConfig={"guardrailIdentifier": "3mfg8d8vj4ee", "guardrailVersion": "3", "trace": "enabled"},
            )

            stop_reason = response.get("stopReason", "end_turn")
            output_message = response["output"]["message"]
            messages.append(latest_message)
            messages.append(output_message)

            if stop_reason == "tool_use":
                tool_results = []
                for block in output_message["content"]:
                    if "toolUse" in block:
                        tool_call = block["toolUse"]
                        tool_name = tool_call["name"]
                        tool_input = tool_call["input"]
                        tool_use_id = tool_call["toolUseId"]
                        tools_used.append(tool_name)

                        print(f"[ReAct] iter={iteration} tool={tool_name} input={json.dumps(tool_input)}")

                        try:
                            result_text = TOOL_DISPATCH[tool_name](tool_input)
                        except Exception as e:
                            result_text = f"Tool error: {str(e)}"

                        tool_results.append({
                            "toolResult": {
                                "toolUseId": tool_use_id,
                                "content": [{"text": result_text}],
                            }
                        })

                messages.append({"role": "user", "content": tool_results})
            else:
                # Final response — extract text
                final_text = ""
                for block in output_message["content"]:
                    if "text" in block:
                        final_text += block["text"]

                # Strip XML tags that Nova sometimes adds
                final_text = re.sub(r'<thinking>.*?</thinking>\s*', '', final_text, flags=re.DOTALL)
                final_text = re.sub(r'</?(?:response|answer|result|output)>\s*', '', final_text)
                final_text = final_text.strip()

                # Save conversation to DynamoDB
                try:
                    conv_table = dynamodb.Table(CONVERSATIONS_TABLE)
                    conv_table.put_item(Item={
                        "farmer_id": farmer_id,
                        "timestamp": datetime.utcnow().isoformat(),
                        "message": message,
                        "response": final_text,
                        "tools_used": tools_used,
                    })
                except Exception as e:
                    print(f"Failed to save conversation: {e}")

                return api_response(200, {
                    "response": final_text,
                    "tools_used": tools_used,
                    "farmer_id": farmer_id,
                })

        # Exhausted all iterations without a final answer
        return api_response(200, {
            "response": "I was unable to fully process your request. Please try a simpler question.",
            "tools_used": tools_used,
            "farmer_id": farmer_id,
        })

    except Exception as e:
        print(f"Chat error: {e}")
        return api_response(500, {"error": f"Agent error: {str(e)}"})


# ==============================================================================
# 9. WHATSAPP/TWILIO WEBHOOK
# ==============================================================================

import urllib.request
import urllib.parse
import urllib.error
from urllib.error import URLError

TWILIO_SECRET_ARN = os.environ.get("TWILIO_SECRET_ARN")
TWILIO_ACCOUNT_SID = None
TWILIO_AUTH_TOKEN = None

def load_twilio_secrets():
    """Load Twilio credentials from AWS Secrets Manager."""
    global TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN
    
    if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
        return True # Already loaded
        
    if not TWILIO_SECRET_ARN:
        print("WARNING: TWILIO_SECRET_ARN environment variable not set.")
        return False
        
    try:
        secrets_client = boto3.client("secretsmanager", region_name=REGION)
        response = secrets_client.get_secret_value(SecretId=TWILIO_SECRET_ARN)
        secret_string = response.get("SecretString")
        if secret_string:
            secrets_dict = json.loads(secret_string)
            TWILIO_ACCOUNT_SID = secrets_dict.get("TWILIO_ACCOUNT_SID")
            TWILIO_AUTH_TOKEN = secrets_dict.get("TWILIO_AUTH_TOKEN")
            return True
    except Exception as e:
        print(f"Failed to load Twilio secrets from Secrets Manager: {e}")
        
    return False

def fetch_twilio_media(media_url):
    """Fetch media from Twilio securely using Basic Auth."""
    load_twilio_secrets() # Ensure secrets are loaded
    
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        print("WARNING: Twilio credentials not set, cannot fetch media securely in production.")
        # Attempt unauthenticated fetch (might fail depending on Twilio settings)
        req = urllib.request.Request(media_url)
    else:
        auth_str = f"{TWILIO_ACCOUNT_SID}:{TWILIO_AUTH_TOKEN}"
        auth_bytes = auth_str.encode("utf-8")
        base64_auth = base64.b64encode(auth_bytes).decode("utf-8")
        req = urllib.request.Request(media_url)
        req.add_header("Authorization", f"Basic {base64_auth}")

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read()
    except Exception as e:
        print(f"Error fetching Twilio media: {e}")
        return None

import time
import uuid
import urllib.request

transcribe_client = boto3.client('transcribe', region_name=REGION)

def transcribe_audio_with_aws_transcribe(audio_bytes, mime_type):
    """Transcribe WhatsApp audio using Amazon Transcribe by temporarily uploading to S3."""
    if not UPLOADS_BUCKET:
        return "(Error: UPLOADS_BUCKET not configured. Cannot process audio.)"

    try:
        # Determine format (valid Transcribe formats: mp3, mp4, wav, flac, ogg, amr, webm)
        ext = "m4a"  # default
        if "ogg" in mime_type: ext = "ogg"
        elif "mp4" in mime_type or "m4a" in mime_type: ext = "mp4"
        elif "webm" in mime_type: ext = "webm"
        elif "mp3" in mime_type: ext = "mp3"
        elif "wav" in mime_type: ext = "wav"
        
        # 1. Upload bytes to S3
        temp_file_key = f"tmp_audio/{uuid.uuid4()}.{ext}"
        s3.put_object(
            Bucket=UPLOADS_BUCKET,
            Key=temp_file_key,
            Body=audio_bytes,
            ContentType=mime_type
        )
        s3_uri = f"s3://{UPLOADS_BUCKET}/{temp_file_key}"
        print(f"Uploaded Twilio audio to {s3_uri}")

        # 2. Start Transcribe Job
        job_name = f"AgriMitra_Audio_{uuid.uuid4()}"
        transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={'MediaFileUri': s3_uri},
            IdentifyLanguage=True,  # Auto-detect language (Hindi, English, etc.)
            MediaFormat=ext
        )

        # 3. Poll for completion (API Gateway times out at 30s, so we wait max 25s)
        max_retries = 12
        sleep_time = 2
        transcript_text = "(Error: Transcription timed out)"
        
        for _ in range(max_retries):
            status = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
            job_status = status['TranscriptionJob']['TranscriptionJobStatus']
            
            if job_status == 'COMPLETED':
                transcript_uri = status['TranscriptionJob']['Transcript']['TranscriptFileUri']
                # Download transcript JSON directly from AWS provided URI
                with urllib.request.urlopen(transcript_uri, timeout=5) as response:
                    body = json.loads(response.read().decode('utf-8'))
                    transcript_text = body['results']['transcripts'][0]['transcript']
                break
            elif job_status == 'FAILED':
                failure_reason = status['TranscriptionJob'].get('FailureReason', 'Unknown reason')
                print(f"Transcribe job failed: {failure_reason}")
                transcript_text = "(Error: Audio transcription failed)"
                break
                
            time.sleep(sleep_time)

        # 4. Clean up S3 audio file
        try:
            s3.delete_object(Bucket=UPLOADS_BUCKET, Key=temp_file_key)
            transcribe_client.delete_transcription_job(TranscriptionJobName=job_name)
        except Exception as cleanup_err:
            print(f"Cleanup error (ignored): {cleanup_err}")

        return transcript_text.strip()

    except Exception as e:
        print(f"Audio transcription error (Amazon Transcribe): {e}")
        return "(Error: Failed to transcribe audio note using AWS Transcribe. Please type your message.)"

def describe_image_with_nova(image_bytes, mime_type):
    """Describe WhatsApp image using Bedrock Nova."""
    try:
        format_map = {"image/jpeg": "jpeg", "image/png": "png", "image/gif": "gif", "image/webp": "webp"}
        image_format = format_map.get(mime_type, "jpeg")

        # Use Nova Lite directly for vision (prompt router doesn't support image input)
        VISION_MODEL_ID = "apac.amazon.nova-lite-v1:0"
        response = bedrock.converse(
            modelId=VISION_MODEL_ID,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "image": {
                            "format": image_format,
                            "source": {"bytes": image_bytes}
                        }
                    },
                    {"text": "Analyze this image from an agricultural perspective. Describe what you see in detail. If it is a plant, note its apparent health and signs of disease or pest. Be concise but descriptive!"}
                ]
            }],
        )
        output_msg = response["output"]["message"]
        for block in output_msg["content"]:
            if "text" in block:
                return block["text"].strip()
        return ""
    except Exception as e:
        print(f"Image description error: {e}")
        return ""


def handle_twilio_webhook(event):
    """Handle POST /sms from Twilio for WhatsApp/SMS users."""
    try:
        body = event.get("body", "")
        if event.get("isBase64Encoded", False):
            try:
                # API Gateway might base64 encode the x-www-form-urlencoded body.
                body = base64.b64decode(body).decode('utf-8')
            except UnicodeDecodeError:
                # If Twilio sends weird characters that break utf-8 decoding (e.g. emojis or bad bytes)
                body = base64.b64decode(body).decode('utf-8', errors='replace')
            
        # Parse URL-encoded form data
        parsed_body = urllib.parse.parse_qs(body)
        
        # Helper to get first item safely
        def get_field(key, default=""):
            val = parsed_body.get(key, [default])
            return val[0] if val else default

        sender_number = get_field("From", "anonymous").strip()
        agent_input_text = get_field("Body", "").strip()
        media_url = get_field("MediaUrl0", "").strip()
        media_content_type = get_field("MediaContentType0", "").strip()
        
        # 0. Background asynchronous invocation check
        is_background_invocation = event.get("is_background", False)
        
        if media_url and not is_background_invocation:
            lambda_client = boto3.client('lambda', region_name=REGION)
            
            async_payload = {
                "body": body,
                "isBase64Encoded": False,  # Body is already decoded at this point
                "is_background": True,
                "rawPath": "/sms",
                "requestContext": {
                    "http": {
                        "method": "POST"
                    }
                }
            }
            
            import os
            current_function_name = os.environ.get('AWS_LAMBDA_FUNCTION_NAME', '')
            
            if current_function_name:
                print(f"Triggering asynchronous background execution of {current_function_name} to avoid Twilio timeout for media processing.")
                lambda_client.invoke(
                    FunctionName=current_function_name,
                    InvocationType='Event',  # Asynchronous
                    Payload=json.dumps(async_payload)
                )
            
            # Reply to Twilio IMMEDIATELY to stop the 15-second timeout
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "text/xml"},
                "body": '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'
            }

        if is_background_invocation:
            print(f"Background WhatsApp execution for: {sender_number}, Text: {agent_input_text}, Media: {media_url}")
        else:
            print(f"Synchronous WhatsApp execution for: {sender_number}, Text: {agent_input_text}")

        # 1. Pre-process Media if present
        if media_url:
            media_bytes = fetch_twilio_media(media_url)
            if not media_bytes:
                agent_input_text = "(Could not securely download the attached media from Twilio)"
            elif media_content_type.startswith("audio/"):
                transcription = transcribe_audio_with_aws_transcribe(media_bytes, media_content_type)
                agent_input_text = transcription if transcription else "(Could not understand the audio)"
            elif media_content_type.startswith("image/"):
                description = describe_image_with_nova(media_bytes, media_content_type)
                # Pass the visual description as a crop diagnosis query — avoid mentioning "image" or "uploaded"
                # so handle_chat doesn't try to call analyze_crop_image with a nonexistent key
                agent_input_text = f"A farmer's crop shows the following visual characteristics: {description}. Based on this, provide diagnosis and advice."
        
        if not agent_input_text:
            # Return a minimal TwiML response indicating no input received
            xml_response = f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>No message received.</Message></Response>'
            return {"statusCode": 200, "headers": {"Content-Type": "text/xml"}, "body": xml_response}

        # 2. Reuse the /chat endpoint logic — no need to duplicate the ReAct loop
        # Construct a fake chat event that handle_chat expects
        load_twilio_secrets()
        
        chat_body = {
            "message": agent_input_text,
            "farmer_id": sender_number,
            "history": [],  # handle_chat fetches history from the client-side; for WhatsApp we skip client history
        }
        
        chat_event = {
            "body": json.dumps(chat_body)
        }
        
        print(f"[Twilio] Delegating to handle_chat with message: {agent_input_text[:100]}...")
        
        chat_response = handle_chat(chat_event)
        
        # Extract the response text from handle_chat's JSON response
        try:
            response_body = json.loads(chat_response.get("body", "{}"))
            final_text = response_body.get("response", "Sorry, I could not process your request.")
        except Exception:
            final_text = "Sorry, I could not process your request."
        
        print(f"[Twilio] handle_chat returned: {final_text[:200]}...")
        
        # Send the response back via Twilio REST API (since we already returned 200 to the webhook)
        if is_background_invocation and TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
            try:
                twilio_number = get_field("To", "")
                send_body = final_text[:1600] if final_text else "Sorry, I could not process your request."
                
                print(f"Sending async Twilio reply from {twilio_number} to {sender_number}...")
                
                data = urllib.parse.urlencode({
                    'To': sender_number,
                    'From': twilio_number,
                    'Body': send_body
                }).encode('utf-8')
                
                url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
                req = urllib.request.Request(url, data=data, method="POST")
                
                auth_str = f"{TWILIO_ACCOUNT_SID}:{TWILIO_AUTH_TOKEN}"
                auth_header = "Basic " + base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
                req.add_header('Authorization', auth_header)
                req.add_header('Content-Type', 'application/x-www-form-urlencoded')
                
                with urllib.request.urlopen(req) as resp:
                    print(f"Twilio API outbound response: {resp.status}")
                    
            except urllib.error.HTTPError as http_err:
                error_body = http_err.read().decode('utf-8', errors='replace')
                print(f"Twilio HTTP Error {http_err.code}: {error_body}")
            except Exception as twilio_err:
                print(f"Failed to send outbound Twilio message: {twilio_err}")
        elif not is_background_invocation:
            # Synchronous path (text messages without media)
            from xml.sax.saxutils import escape
            if not final_text:
                final_text = "Sorry, I could not process your request."
            escaped_text = escape(final_text)
            xml_response = f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{escaped_text}</Message></Response>'
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "text/xml"},
                "body": xml_response
            }
        
        return {"statusCode": 200, "body": "Processing complete"}

    except Exception as e:
        print(f"WhatsApp webhook error: {e}")
        xml_error = '<?xml version="1.0" encoding="UTF-8"?><Response><Message>Sorry, an internal error occurred.</Message></Response>'
        return {"statusCode": 500, "headers": {"Content-Type": "text/xml"}, "body": xml_error}
