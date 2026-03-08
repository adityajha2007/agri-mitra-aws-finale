"""
Seed script for Agri-Mitra DynamoDB tables and S3 buckets.
Populates mandi prices, weather cache, news, policy documents, farmers.

Usage:
    cd backend
    python seed_data.py
"""

import json
import random
import boto3
from decimal import Decimal
from datetime import datetime, timedelta

REGION = "ap-south-1"
TODAY = datetime.now().strftime("%Y-%m-%d")

# S3 buckets
POLICIES_BUCKET = "agrimitradata-policiesbucketa55120c1-8f2zml02rpj3"
UPLOADS_BUCKET = "agrimitradata-uploadsbucket5e5e9b64-swpgkwc4hwiq"

# DynamoDB table names
TABLE_MANDI = "agri-mitra-mandi-prices"
TABLE_WEATHER = "agri-mitra-weather-cache"
TABLE_NEWS = "agri-mitra-news"
TABLE_POLICY = "agri-mitra-policy-documents"
TABLE_FARMERS = "agri-mitra-farmers"

dynamodb = boto3.resource("dynamodb", region_name=REGION)
s3 = boto3.client("s3", region_name=REGION)
bedrock = boto3.client("bedrock-runtime", region_name=REGION)


# ---------------------------------------------------------------------------
# 1. Mandi Prices
# ---------------------------------------------------------------------------

CROPS = {
    "wheat":      (2000, 2400),
    "rice":       (2600, 3200),
    "onion":      (1400, 2200),
    "tomato":     (800, 1600),
    "potato":     (700, 1200),
    "maize":      (1800, 2200),
    "cotton":     (6000, 7500),
    "soyabean":   (4000, 5000),
    "mustard":    (4500, 5500),
    "sugarcane":  (300, 400),
}

MARKETS = [
    ("Lucknow", "Uttar Pradesh"),
    ("Pune", "Maharashtra"),
    ("Mumbai", "Maharashtra"),
    ("Jaipur", "Rajasthan"),
    ("Bhopal", "Madhya Pradesh"),
    ("Varanasi", "Uttar Pradesh"),
    ("Nagpur", "Maharashtra"),
    ("Bangalore", "Karnataka"),
    ("Hyderabad", "Telangana"),
    ("Chennai", "Tamil Nadu"),
    ("Kolkata", "West Bengal"),
    ("Patna", "Bihar"),
    ("Indore", "Madhya Pradesh"),
    ("Nashik", "Maharashtra"),
    ("Agra", "Uttar Pradesh"),
]


def seed_mandi_prices():
    table = dynamodb.Table(TABLE_MANDI)
    count = 0
    
    # Generate daily prices for the last 90 days for SARIMA modeling
    today = datetime.now()
    
    for crop_name, (low, high) in CROPS.items():
        for market_name, state in MARKETS:
            # Generate 90 days of historical data
            for days_ago in range(90, -1, -1):
                date = (today - timedelta(days=days_ago)).strftime("%Y-%m-%d")
                
                # Add some trend and seasonality to prices
                base_price = (low + high) // 2
                trend = days_ago * 2  # Slight upward trend
                seasonal = int(50 * (1 + 0.5 * ((days_ago % 30) / 30)))  # Monthly cycle
                noise = random.randint(-100, 100)
                
                price = base_price - trend + seasonal + noise
                price = max(low, min(high, price))  # Keep within bounds
                
                spread = random.randint(50, 150)
                min_price = price - spread
                max_price = price + spread
                arrivals = random.randint(50, 800)

                item = {
                    "crop_name": crop_name,
                    "market_date": f"{market_name}#{date}",
                    "market_name": market_name,
                    "state": state,
                    "price_per_quintal": Decimal(str(price)),
                    "arrivals": arrivals,
                    "min_price": Decimal(str(min_price)),
                    "max_price": Decimal(str(max_price)),
                    "date": date,
                }
                table.put_item(Item=item)
                count += 1
                
                if days_ago == 0:  # Only print today's prices
                    print(f"  [mandi] {crop_name} @ {market_name}: Rs {price}/q (today)")
    
    print(f"  => Inserted {count} mandi-price records (90 days of daily data).\n")


# ---------------------------------------------------------------------------
# 2. Weather Cache
# ---------------------------------------------------------------------------

DISTRICTS_WEATHER = {
    "Lucknow": {
        "temp_min": 18, "temp_max": 33, "humidity": 45, "rainfall_mm": 0,
        "wind_speed_kmh": 12, "description": "Clear skies with warm afternoon",
        "advisory": "Wheat crop is in grain-filling stage. Avoid irrigation now as harvest approaches in 2-3 weeks. Monitor for yellow rust symptoms on leaves and apply fungicide if spotted early. Plan harvesting equipment availability."
    },
    "Pune": {
        "temp_min": 19, "temp_max": 35, "humidity": 35, "rainfall_mm": 0,
        "wind_speed_kmh": 10, "description": "Sunny and dry with mild breeze",
        "advisory": "Rabi jowar harvest can begin if grain is hard and moisture below 12%. For onion crops, reduce irrigation frequency as bulb maturation progresses. Prepare storage facilities for upcoming harvest."
    },
    "Mumbai": {
        "temp_min": 23, "temp_max": 34, "humidity": 65, "rainfall_mm": 0,
        "wind_speed_kmh": 14, "description": "Hazy sunshine with coastal humidity",
        "advisory": "High humidity may promote fungal diseases in vegetable crops. Apply neem-based spray on leafy vegetables as preventive measure. Ensure proper drainage in low-lying fields near coastal areas."
    },
    "Jaipur": {
        "temp_min": 16, "temp_max": 34, "humidity": 28, "rainfall_mm": 0,
        "wind_speed_kmh": 18, "description": "Hot and dry with strong winds",
        "advisory": "Mustard harvesting is in full swing. Thresh the crop when pods turn brown and seeds rattle inside. Strong winds can cause shattering losses — harvest early morning when humidity is slightly higher."
    },
    "Bhopal": {
        "temp_min": 17, "temp_max": 34, "humidity": 38, "rainfall_mm": 0,
        "wind_speed_kmh": 11, "description": "Warm and dry, partly cloudy",
        "advisory": "Wheat and chickpea crops are maturing. Apply terminal irrigation if soil moisture is very low for proper grain development. Watch for pod borer in chickpea — use pheromone traps for monitoring."
    },
    "Varanasi": {
        "temp_min": 19, "temp_max": 35, "humidity": 48, "rainfall_mm": 0,
        "wind_speed_kmh": 9, "description": "Warm and hazy, light breeze",
        "advisory": "Late-sown wheat needs one more protective irrigation for proper grain filling. Check potato fields for late blight signs given morning dew conditions. Plan harvest logistics for wheat within 15-20 days."
    },
    "Nagpur": {
        "temp_min": 20, "temp_max": 37, "humidity": 30, "rainfall_mm": 0,
        "wind_speed_kmh": 13, "description": "Hot and dry with clear skies",
        "advisory": "Orange orchards need careful water management as fruit sizing continues. Apply mulching around citrus trees to conserve soil moisture. Cotton stubble removal should be completed before pre-monsoon ploughing."
    },
    "Bangalore": {
        "temp_min": 19, "temp_max": 32, "humidity": 42, "rainfall_mm": 2,
        "wind_speed_kmh": 8, "description": "Pleasant with light scattered showers possible",
        "advisory": "Pre-monsoon light showers benefit ragi and finger millet sowing preparations. Tomato and capsicum crops in polyhouses need adequate ventilation. Good time for land preparation and green manure incorporation."
    },
    "Hyderabad": {
        "temp_min": 21, "temp_max": 36, "humidity": 40, "rainfall_mm": 0,
        "wind_speed_kmh": 15, "description": "Hot and dry with gusty winds",
        "advisory": "Cotton fields should be cleared of old stalks to disrupt pink bollworm lifecycle. Maize Rabi crop harvest can begin where cobs are fully dried. Prepare rice nursery beds for upcoming Kharif season planning."
    },
    "Chennai": {
        "temp_min": 24, "temp_max": 33, "humidity": 72, "rainfall_mm": 1,
        "wind_speed_kmh": 16, "description": "Warm and humid with sea breeze",
        "advisory": "Summer paddy transplanting can continue with SRI method for better yield. Coastal humidity favours leaf folder pest in rice — install light traps. Banana plantations need regular irrigation and de-suckering."
    },
    "Kolkata": {
        "temp_min": 22, "temp_max": 33, "humidity": 68, "rainfall_mm": 0,
        "wind_speed_kmh": 10, "description": "Warm and humid, partly cloudy",
        "advisory": "Boro rice is in panicle initiation stage — ensure 5 cm standing water in fields. Apply potash top dressing for better grain quality. Jute seed bed preparation should begin for April sowing."
    },
    "Patna": {
        "temp_min": 18, "temp_max": 33, "humidity": 52, "rainfall_mm": 0,
        "wind_speed_kmh": 11, "description": "Warm with haze, clearing by afternoon",
        "advisory": "Wheat crop is approaching physiological maturity. Stop irrigation when ear heads turn golden. For maize Rabi crop, cob picking can start when husk dries. Litchi orchards need light irrigation for fruit set."
    },
    "Indore": {
        "temp_min": 17, "temp_max": 35, "humidity": 32, "rainfall_mm": 0,
        "wind_speed_kmh": 14, "description": "Hot and dry, clear skies",
        "advisory": "Soyabean fields from Kharif should be prepared for summer moong sowing after wheat harvest. Garlic crop is ready for harvesting — cure bulbs in shade for 7-10 days before storage. Apply gypsum to groundnut if sowing planned."
    },
    "Nashik": {
        "temp_min": 16, "temp_max": 35, "humidity": 33, "rainfall_mm": 0,
        "wind_speed_kmh": 12, "description": "Hot days with cool mornings",
        "advisory": "Grape harvest season is concluding. Post-harvest pruning should be planned within 15 days. Onion Rabi crop lifting can begin when 50% tops fall over. Ensure proper curing before storage to reduce losses."
    },
    "Agra": {
        "temp_min": 17, "temp_max": 34, "humidity": 40, "rainfall_mm": 0,
        "wind_speed_kmh": 15, "description": "Warm with dusty winds in afternoon",
        "advisory": "Potato cold storage operations are critical — maintain temperature at 2-4 degrees C. Wheat harvest will commence in 2 weeks — arrange combine harvesters in advance. Mustard threshing should be done on clean floors to avoid contamination."
    },
}


def seed_weather():
    table = dynamodb.Table(TABLE_WEATHER)
    count = 0
    for district, data in DISTRICTS_WEATHER.items():
        item = {
            "district": district,
            "date": TODAY,
            "temperature_min": data["temp_min"],
            "temperature_max": data["temp_max"],
            "humidity": data["humidity"],
            "rainfall_mm": Decimal(str(data["rainfall_mm"])),
            "wind_speed_kmh": data["wind_speed_kmh"],
            "description": data["description"],
            "agricultural_advisory": data["advisory"],
        }
        table.put_item(Item=item)
        count += 1
        print(f"  [weather] {district}: {data['temp_min']}-{data['temp_max']}C, {data['description']}")
    print(f"  => Inserted {count} weather records.\n")


# ---------------------------------------------------------------------------
# 3. News
# ---------------------------------------------------------------------------

def _ts(days_ago, hour):
    """Generate ISO timestamp days_ago from TODAY at given hour."""
    dt = datetime.now().replace(hour=hour, minute=random.randint(0, 59), second=random.randint(0, 59)) - timedelta(days=days_ago)
    return dt.isoformat() + "Z"


NEWS_ITEMS = [
    # policy (4)
    {
        "category": "policy",
        "timestamp": _ts(0, 9),
        "title": "Cabinet Approves 8% Increase in MSP for Kharif 2026 Crops",
        "summary": "The Union Cabinet has approved an increase of 7-8% in Minimum Support Prices for all major Kharif crops for the 2026-27 season. Paddy MSP has been raised to Rs 2,450 per quintal, while cotton MSP sees the highest jump at Rs 7,521 per quintal, benefiting over 10 crore farming households.",
        "source_url": "https://pib.gov.in/kharif-msp-2026",
        "relevance_tags": ["MSP", "kharif", "paddy", "cotton", "government policy"],
    },
    {
        "category": "policy",
        "timestamp": _ts(1, 14),
        "title": "PM-KISAN 20th Installment Released: Rs 2,000 Credited to 9.5 Crore Farmers",
        "summary": "Prime Minister released the 20th installment of PM-KISAN Samman Nidhi, transferring Rs 19,000 crore directly to bank accounts of 9.5 crore eligible farmer families. Farmers can check their payment status on the PM-KISAN portal or through the mobile app.",
        "source_url": "https://pmkisan.gov.in/installment-20",
        "relevance_tags": ["PM-KISAN", "direct benefit transfer", "farmer income"],
    },
    {
        "category": "policy",
        "timestamp": _ts(2, 10),
        "title": "PMFBY Claims Settlement Deadline Extended for Rabi 2025-26 Season",
        "summary": "The Agriculture Ministry has directed insurance companies to settle all pending Pradhan Mantri Fasal Bima Yojana claims for Rabi 2025-26 within 30 days. States including Madhya Pradesh, Rajasthan, and Maharashtra have the highest pending claims. Farmers can track claim status via the PMFBY mobile app.",
        "source_url": "https://pmfby.gov.in/claims-rabi-2026",
        "relevance_tags": ["PMFBY", "crop insurance", "Rabi", "claims"],
    },
    {
        "category": "policy",
        "timestamp": _ts(2, 16),
        "title": "Government Launches Digital Agriculture Mission with Rs 2,800 Crore Outlay",
        "summary": "The Ministry of Agriculture has launched the Digital Agriculture Mission to create digital infrastructure for Indian agriculture, including AgriStack farmer registry, soil health digital records, and AI-powered advisory systems. The mission aims to cover all 14 crore farming households by 2028.",
        "source_url": "https://agricoop.gov.in/digital-mission-2026",
        "relevance_tags": ["digital agriculture", "AgriStack", "technology", "government"],
    },
    # market (4)
    {
        "category": "market",
        "timestamp": _ts(0, 8),
        "title": "Onion Prices Surge 25% in Delhi Azadpur Mandi Amid Supply Shortage",
        "summary": "Onion prices at Delhi's Azadpur wholesale market have risen sharply to Rs 2,100 per quintal as arrivals from Maharashtra and Madhya Pradesh decline. The late Kharif crop has been exhausted and Rabi crop arrivals from Nashik are yet to peak. Government is monitoring the situation and may release buffer stock.",
        "source_url": "https://agmarknet.gov.in/onion-prices-march-2026",
        "relevance_tags": ["onion", "prices", "Delhi", "Azadpur", "supply"],
    },
    {
        "category": "market",
        "timestamp": _ts(0, 15),
        "title": "Wheat Procurement at MSP Begins Across Punjab, Haryana and UP",
        "summary": "Government agencies including FCI have begun Rabi wheat procurement at the MSP of Rs 2,375 per quintal across major wheat-producing states. Over 5,000 procurement centres have been set up. Punjab targets procurement of 130 lakh tonnes while UP aims for 60 lakh tonnes this season.",
        "source_url": "https://fci.gov.in/wheat-procurement-2026",
        "relevance_tags": ["wheat", "procurement", "MSP", "FCI", "Punjab", "UP"],
    },
    {
        "category": "market",
        "timestamp": _ts(1, 11),
        "title": "Cotton Exports Rise 40% as Global Demand Rebounds",
        "summary": "India's cotton exports have surged by 40% year-on-year reaching 35 lakh bales in the current season, driven by strong demand from Bangladesh, Vietnam and China. This has supported domestic cotton prices which are currently trading above MSP in most mandis across Gujarat and Maharashtra.",
        "source_url": "https://cotcorp.org.in/exports-2026",
        "relevance_tags": ["cotton", "exports", "prices", "Gujarat", "Maharashtra"],
    },
    {
        "category": "market",
        "timestamp": _ts(2, 13),
        "title": "Tomato Prices Crash Below Rs 10/kg in Karnataka as Bumper Harvest Arrives",
        "summary": "Tomato prices have plummeted to Rs 800-900 per quintal at Bangalore KR Market as bumper Rabi production from Kolar and Chikkaballapur districts floods the market. Farmer organizations are demanding government intervention and direct procurement to protect grower interests.",
        "source_url": "https://agmarknet.gov.in/tomato-karnataka-2026",
        "relevance_tags": ["tomato", "prices", "Karnataka", "Bangalore", "oversupply"],
    },
    # technology (4)
    {
        "category": "technology",
        "timestamp": _ts(0, 12),
        "title": "ICAR Releases 5 New Climate-Resilient Wheat Varieties for Northern Plains",
        "summary": "The Indian Council of Agricultural Research has released five new wheat varieties — DBW 370, HD 3386, PBW 896, WH 1270 and HI 1650 — that are tolerant to terminal heat stress and yellow rust. These varieties yield 15-20% more than existing varieties under late-sown conditions prevalent in UP and Bihar.",
        "source_url": "https://icar.org.in/wheat-varieties-2026",
        "relevance_tags": ["ICAR", "wheat", "varieties", "climate resilient", "technology"],
    },
    {
        "category": "technology",
        "timestamp": _ts(1, 9),
        "title": "Drone Spraying Now Permitted for 30 Additional Pesticides: DGCA Notification",
        "summary": "The Directorate General of Civil Aviation has approved 30 additional pesticides and bio-agents for drone-based aerial spraying, taking the total to 85 approved formulations. This will enable faster pest management across cotton, paddy and horticulture crops, reducing labour costs by up to 60%.",
        "source_url": "https://dgca.gov.in/drone-agri-spraying-2026",
        "relevance_tags": ["drones", "pesticides", "DGCA", "technology", "spraying"],
    },
    {
        "category": "technology",
        "timestamp": _ts(2, 7),
        "title": "Nano Urea Adoption Crosses 10 Crore Bottles Mark: IFFCO",
        "summary": "IFFCO has announced that cumulative sales of Nano Urea liquid fertilizer have crossed 10 crore bottles, covering over 4 crore hectares of farmland. Field trials show 8% average yield improvement with 50% reduction in conventional urea usage. The product is now available at Rs 225 per 500ml bottle at all cooperative societies.",
        "source_url": "https://iffco.in/nano-urea-milestone-2026",
        "relevance_tags": ["nano urea", "IFFCO", "fertilizer", "technology"],
    },
    {
        "category": "technology",
        "timestamp": _ts(1, 16),
        "title": "Solar Pump Subsidy Under PM-KUSUM Extended to 2028 with Increased Coverage",
        "summary": "The government has extended the PM-KUSUM scheme for solar pump distribution until 2028 with a target of 35 lakh solar pumps. Component-B now provides 60% subsidy for pumps up to 10 HP. Farmers in Rajasthan, Gujarat and Maharashtra have been the top beneficiaries with over 5 lakh installations completed.",
        "source_url": "https://mnre.gov.in/pm-kusum-extension-2026",
        "relevance_tags": ["solar pump", "PM-KUSUM", "irrigation", "renewable energy"],
    },
    # weather (4)
    {
        "category": "weather",
        "timestamp": _ts(0, 6),
        "title": "IMD Forecasts Early Onset of Pre-Monsoon Showers in South India",
        "summary": "The India Meteorological Department has predicted that pre-monsoon thundershower activity will commence over Kerala and Karnataka by the second week of March, about 10 days earlier than normal. This may benefit summer crop sowing but could disrupt ongoing Rabi harvesting in northern Karnataka.",
        "source_url": "https://mausam.imd.gov.in/premonsoon-2026",
        "relevance_tags": ["IMD", "pre-monsoon", "Kerala", "Karnataka", "weather forecast"],
    },
    {
        "category": "weather",
        "timestamp": _ts(1, 7),
        "title": "Heat Wave Warning Issued for Central India: March 8-12",
        "summary": "IMD has issued a heat wave warning for parts of Madhya Pradesh, Vidarbha, Chhattisgarh and western Odisha from March 8-12 with maximum temperatures expected to cross 42 degrees Celsius. Farmers advised to provide shade for livestock, irrigate crops during evening hours, and avoid field work between 11 AM and 4 PM.",
        "source_url": "https://mausam.imd.gov.in/heatwave-alert-march-2026",
        "relevance_tags": ["heat wave", "central India", "IMD", "advisory"],
    },
    {
        "category": "weather",
        "timestamp": _ts(2, 8),
        "title": "Western Disturbance Brings Unseasonal Rain to Punjab and Haryana",
        "summary": "A strong western disturbance caused light to moderate rainfall across Punjab, Haryana and western UP on March 3-4, bringing temporary relief from rising temperatures. While the rain benefits late-sown wheat, it may cause lodging in mature wheat crop. Farmers are advised to delay harvesting by 3-4 days until the crop dries.",
        "source_url": "https://mausam.imd.gov.in/wd-march-2026",
        "relevance_tags": ["western disturbance", "rain", "Punjab", "Haryana", "wheat"],
    },
    {
        "category": "weather",
        "timestamp": _ts(0, 17),
        "title": "Monsoon 2026 Likely to Be Normal at 98% of LPA: IMD First Forecast",
        "summary": "IMD has released its first long-range forecast for Southwest Monsoon 2026, predicting normal rainfall at 98% of the Long Period Average with a model error of plus-minus 5%. La Nina conditions are expected to prevail during June-September, which historically supports good monsoon rainfall over India.",
        "source_url": "https://mausam.imd.gov.in/monsoon-forecast-2026",
        "relevance_tags": ["monsoon", "forecast", "IMD", "La Nina", "rainfall"],
    },
    # general (4)
    {
        "category": "general",
        "timestamp": _ts(0, 11),
        "title": "National Agriculture Fair 2026 to Be Held in New Delhi from March 15-18",
        "summary": "The annual Krishi Unnati Mela organized by ICAR will be held at Pusa Campus, New Delhi from March 15-18, showcasing latest agricultural technologies, improved seeds, farm machinery, and organic farming practices. Over 500 exhibitors and 5 lakh visitors are expected. Entry is free for farmers with valid ID.",
        "source_url": "https://icar.org.in/krishi-mela-2026",
        "relevance_tags": ["Krishi Mela", "ICAR", "exhibition", "New Delhi"],
    },
    {
        "category": "general",
        "timestamp": _ts(1, 10),
        "title": "Organic Farming Area in India Crosses 50 Lakh Hectares Milestone",
        "summary": "India's total area under certified organic farming has crossed 50 lakh hectares, making it the country with the largest organic farmland globally. Madhya Pradesh leads with 12 lakh hectares followed by Rajasthan and Maharashtra. The organic food market in India is now worth Rs 15,000 crore annually.",
        "source_url": "https://agricoop.gov.in/organic-farming-progress-2026",
        "relevance_tags": ["organic farming", "certification", "Madhya Pradesh"],
    },
    {
        "category": "general",
        "timestamp": _ts(2, 15),
        "title": "FPO Registration Crosses 25,000 Mark Under 10,000 FPO Scheme",
        "summary": "The formation and registration of Farmer Producer Organizations has crossed 25,000 under the Central Government's scheme for formation of 10,000 new FPOs (expanded target). These FPOs collectively represent over 30 lakh farmer members and have facilitated Rs 8,000 crore in agricultural commodity trade.",
        "source_url": "https://sfac.in/fpo-progress-2026",
        "relevance_tags": ["FPO", "farmer organizations", "collective marketing"],
    },
    {
        "category": "general",
        "timestamp": _ts(1, 18),
        "title": "Agriculture Exports Touch Record $55 Billion in FY2025-26",
        "summary": "India's agriculture and allied exports have reached a record $55 billion in FY2025-26, driven by strong demand for rice, spices, marine products and sugar. The government's Agriculture Export Policy target of $60 billion by 2027 appears achievable. Basmati rice remains the single largest export commodity at $6.2 billion.",
        "source_url": "https://apeda.gov.in/exports-fy26",
        "relevance_tags": ["agriculture exports", "basmati rice", "spices", "APEDA"],
    },
]


def seed_news():
    table = dynamodb.Table(TABLE_NEWS)
    count = 0
    for item in NEWS_ITEMS:
        table.put_item(Item=item)
        count += 1
        print(f"  [news] [{item['category']}] {item['title'][:70]}...")
    print(f"  => Inserted {count} news records.\n")


# ---------------------------------------------------------------------------
# 4. Policy Documents + S3
# ---------------------------------------------------------------------------

POLICY_DOCS = {
    "pm-kisan": {
        "title": "PM-KISAN Direct Benefit Transfer",
        "category": "income_support",
        "text": (
            "The Pradhan Mantri Kisan Samman Nidhi (PM-KISAN) is a central government scheme that provides "
            "income support of Rs 6,000 per year to all landholding farmer families across the country. The "
            "amount is transferred directly to the bank accounts of eligible farmers in three equal installments "
            "of Rs 2,000 each, every four months. Launched in February 2019, the scheme covers approximately "
            "10 crore farmer families and has disbursed over Rs 2.8 lakh crore in cumulative transfers.\n\n"
            "Eligibility extends to all farmer families with cultivable landholding, subject to certain exclusion "
            "criteria. Institutional landholders, former and present holders of constitutional posts, serving or "
            "retired officers and employees of state/central government, income tax payers, and professionals "
            "like doctors, engineers and lawyers are excluded. Registration can be done through Common Service "
            "Centres (CSC), state nodal officers, or directly on the PM-KISAN portal at pmkisan.gov.in. "
            "Required documents include Aadhaar card, land ownership records, and bank account details.\n\n"
            "Farmers can check their payment status, update Aadhaar details, and raise grievances through the "
            "PM-KISAN mobile app or the web portal. E-KYC through Aadhaar-based OTP verification is mandatory "
            "for receiving installments. State governments are responsible for identifying eligible farmers and "
            "uploading beneficiary data on the PM-KISAN portal. Any discrepancy in land records or Aadhaar "
            "details may lead to payment delays, and farmers are advised to contact their local agriculture "
            "department or block development officer for resolution."
        ),
    },
    "pmfby": {
        "title": "Pradhan Mantri Fasal Bima Yojana (Crop Insurance)",
        "category": "insurance",
        "text": (
            "Pradhan Mantri Fasal Bima Yojana (PMFBY) is the flagship crop insurance scheme of the Government "
            "of India, designed to provide comprehensive risk coverage to farmers against crop loss due to "
            "natural calamities, pests, and diseases. The scheme operates on an area-approach basis, with the "
            "premium rates fixed at 2% for Kharif crops, 1.5% for Rabi crops, and 5% for annual commercial and "
            "horticultural crops. The balance premium is shared between the Central and State governments. The "
            "scheme covers over 4 crore farmer applications annually with sum insured exceeding Rs 2.5 lakh crore.\n\n"
            "Enrollment under PMFBY is voluntary for all farmers, including loanee farmers since Kharif 2020. "
            "Farmers can enroll through their bank, Common Service Centre, insurance company agents, or directly "
            "through the PMFBY portal and Crop Insurance App. The last date for enrollment is typically one month "
            "before the normal sowing season. Required documents include land records (khatauni/7/12 extract), "
            "sowing certificate from the patwari or agriculture officer, bank account details, and Aadhaar card. "
            "Share-croppers and tenant farmers can also enroll with appropriate documentation.\n\n"
            "Claims assessment uses a combination of Crop Cutting Experiments (CCEs), remote sensing technology, "
            "weather data, and satellite imagery. For localized calamities like hailstorm and landslide, and for "
            "post-harvest losses due to unseasonal rain, individual farm-level assessment is conducted. Farmers "
            "must report crop loss within 72 hours through the Crop Insurance App, toll-free number 14447, or "
            "at their nearest agriculture office. Claims are to be settled within two months of harvest. The "
            "scheme also provides prevented sowing coverage — if a farmer is unable to sow due to adverse weather, "
            "25% of the sum insured is payable as claim."
        ),
    },
    "msp-policy-2026": {
        "title": "Minimum Support Price Policy 2026",
        "category": "pricing",
        "text": (
            "The Minimum Support Price (MSP) policy is a key agricultural price support mechanism through which "
            "the Government of India sets floor prices for 23 major agricultural commodities covering cereals "
            "(paddy, wheat, maize, jowar, bajra, ragi, barley), pulses (chana, tur, moong, urad, masoor), "
            "oilseeds (groundnut, mustard/rapeseed, soyabean, sunflower, sesame, niger seed, safflower), and "
            "commercial crops (cotton, jute, copra, sugarcane). MSP is announced by the Central Government on "
            "the recommendation of the Commission for Agricultural Costs and Prices (CACP).\n\n"
            "For the Rabi season 2025-26, the MSP for wheat has been fixed at Rs 2,375 per quintal, mustard at "
            "Rs 5,950 per quintal, chana at Rs 5,650 per quintal, and masoor at Rs 6,700 per quintal, "
            "ensuring a minimum of 50% return over the all-India weighted average cost of production (A2+FL). "
            "Government procurement is conducted through agencies like FCI for wheat and rice, NAFED for pulses "
            "and oilseeds, and CCI for cotton. Procurement centres are set up across major producing states "
            "during the harvest season.\n\n"
            "Farmers can sell their produce at MSP at designated procurement centres by providing their Aadhaar "
            "card, land records, and bank account details. Payments are made directly to farmer bank accounts "
            "within 48-72 hours of procurement. States like Punjab, Haryana, Madhya Pradesh and Chhattisgarh "
            "have extensive MSP procurement networks, while procurement coverage is being expanded in eastern "
            "states like Bihar, Jharkhand and West Bengal. The PM-AASHA scheme provides additional price support "
            "for oilseeds and pulses through Price Support Scheme (PSS), Price Deficiency Payment Scheme (PDPS), "
            "and Private Procurement and Stockist Scheme (PPSS)."
        ),
    },
    "soil-health-card": {
        "title": "Soil Health Card Scheme",
        "category": "soil_management",
        "text": (
            "The Soil Health Card (SHC) Scheme, launched in February 2015, aims to provide soil health cards to "
            "all farmers in the country at regular intervals of two years. Each card carries crop-wise "
            "recommendations for nutrients and fertilizers required for individual farms, helping farmers improve "
            "productivity through balanced and judicious use of fertilizers. Over 23 crore soil health cards have "
            "been distributed across two cycles of the scheme, covering nearly all operational landholdings.\n\n"
            "The soil health card provides information on 12 key parameters: primary nutrients (Nitrogen, "
            "Phosphorus, Potassium), secondary nutrients (Sulphur, Calcium, Magnesium), and micro-nutrients "
            "(Zinc, Iron, Copper, Manganese, Boron) along with physical parameters like pH and Electrical "
            "Conductivity. Based on soil test results, the card provides crop-wise fertilizer recommendations "
            "indicating the exact dosage of nitrogen, phosphorus, potash and other nutrients needed. This helps "
            "reduce excessive fertilizer use, which currently causes soil degradation in many parts of India.\n\n"
            "Farmers can access their soil health card online through the SHC portal (soilhealth.dac.gov.in) by "
            "entering their state, district, village and farmer details. New soil testing can be requested "
            "through the local agriculture department or Krishi Vigyan Kendra (KVK). The government has set up "
            "over 2,000 soil testing laboratories and 5,000 mini-labs across the country. Studies show that "
            "farmers who followed SHC recommendations achieved 10-15% reduction in fertilizer costs and 5-8% "
            "improvement in crop yields. Integration with the Fertilizer Subsidy DBT system is underway to link "
            "fertilizer purchase recommendations directly with SHC data."
        ),
    },
    "pmksy-irrigation": {
        "title": "PM Krishi Sinchai Yojana (Irrigation)",
        "category": "irrigation",
        "text": (
            "Pradhan Mantri Krishi Sinchai Yojana (PMKSY) was launched in 2015 with the motto 'Har Khet Ko Paani' "
            "(water to every field) and 'More Crop Per Drop' to expand cultivated area under assured irrigation, "
            "improve on-farm water use efficiency, and promote sustainable water conservation practices. The "
            "scheme has been allocated Rs 93,068 crore for the period 2021-2026 and integrates multiple water "
            "management programs under a single umbrella.\n\n"
            "PMKSY has four key components: Accelerated Irrigation Benefits Programme (AIBP) for completion of "
            "major and medium irrigation projects; Har Khet Ko Paani for creating new water sources, repairing "
            "and restoring water bodies, and strengthening canal distribution network; Per Drop More Crop for "
            "promoting micro irrigation (drip and sprinkler systems) with subsidy of 55% for small and marginal "
            "farmers and 45% for other farmers; and Watershed Development for rainwater harvesting, soil "
            "moisture conservation and groundwater recharge in rainfed areas.\n\n"
            "Under the micro irrigation component, farmers can avail subsidy for drip irrigation systems, "
            "sprinkler systems, rain gun systems, and centre pivot systems. Applications can be submitted "
            "through the state agriculture/horticulture department or online on the respective state portal. "
            "Priority is given to drought-prone districts, tribal areas, and regions with groundwater depletion. "
            "Over 75 lakh hectares have been brought under micro irrigation since the scheme's inception. The "
            "scheme also supports community irrigation projects including farm ponds, check dams, and percolation "
            "tanks, with up to 90% government funding for projects in tribal and hilly areas."
        ),
    },
    "nmsa-sustainable": {
        "title": "National Mission on Sustainable Agriculture",
        "category": "sustainability",
        "text": (
            "The National Mission for Sustainable Agriculture (NMSA) is one of the eight Missions under the "
            "National Action Plan on Climate Change (NAPCC), aimed at making Indian agriculture more productive, "
            "sustainable, and climate resilient. The mission focuses on ten key dimensions: improved crop seeds "
            "and livestock, water use efficiency, pest management, improved farm practices, nutrient management, "
            "agricultural insurance, credit support, markets, access to information, and livelihood diversification. "
            "NMSA integrates several sub-schemes including Rainfed Area Development (RAD), Soil Health Management "
            "(SHM), and Climate Change and Sustainable Agriculture Monitoring (CCSAMM).\n\n"
            "Under the Rainfed Area Development programme, the scheme promotes Integrated Farming Systems (IFS) "
            "approach covering crops, livestock, fisheries, forestry and bee-keeping suitable for rainfed regions. "
            "Farmers receive assistance of Rs 12,500 per hectare for adoption of integrated farming systems. "
            "The Soil Health Management component supports setting up of soil testing laboratories, promotion of "
            "organic fertilizers like vermicompost and bio-fertilizers, and reclamation of problematic soils "
            "including acid, saline and alkaline soils.\n\n"
            "The mission also runs the Paramparagat Krishi Vikas Yojana for organic farming and Sub-Mission on "
            "Agroforestry for promoting tree plantation on farm lands. Climate resilient agriculture practices "
            "like zero tillage, raised bed planting, direct seeded rice, crop residue management, and stress-"
            "tolerant crop varieties are promoted through Krishi Vigyan Kendras and state agriculture departments. "
            "Farmers can access NMSA benefits through their district agriculture office. The mission has reached "
            "over 2 crore farmers across 650 districts with various climate adaptation interventions."
        ),
    },
    "enam-market": {
        "title": "eNAM Electronic Market Platform",
        "category": "marketing",
        "text": (
            "The Electronic National Agriculture Market (eNAM) is a pan-India electronic trading portal that "
            "networks the existing Agricultural Produce Market Committee (APMC) mandis to create a unified "
            "national market for agricultural commodities. Launched in April 2016, eNAM currently integrates "
            "over 1,361 mandis across 23 states and 3 UTs, with more than 1.76 crore registered farmers and "
            "2.5 lakh traders. The platform enables transparent price discovery through online bidding and "
            "ensures farmers receive competitive prices for their produce.\n\n"
            "Farmers can register on eNAM through their local APMC mandi by providing Aadhaar card, bank "
            "account details, and a valid mobile number. Once registered, they receive a unique eNAM ID and can "
            "access the platform through the eNAM mobile app or web portal. The trading process involves: the "
            "farmer brings produce to the mandi, quality assessment is done (manual or through e-quality "
            "parameters), the produce is listed on eNAM with quality details, traders from across the country "
            "can place bids, and the highest bid wins. Payment is settled electronically to the farmer's bank "
            "account within 24-48 hours.\n\n"
            "Key features include: quality assaying infrastructure (moisture meters, cleaners, graders) at "
            "integrated mandis; FPO trading module allowing Farmer Producer Organizations to trade in bulk; "
            "warehouse-based trading enabling farmers to trade from accredited warehouses without physically "
            "bringing produce to mandi; inter-state trade allowing buyers from one state to purchase from mandis "
            "in another state; and logistics support integration. The platform lists over 200 commodities "
            "including cereals, pulses, oilseeds, spices, fruits and vegetables. The eNAM helpline (1800-270-0224) "
            "provides assistance in multiple regional languages."
        ),
    },
    "paramparagat-organic": {
        "title": "Paramparagat Krishi Vikas Yojana (Organic Farming)",
        "category": "organic_farming",
        "text": (
            "Paramparagat Krishi Vikas Yojana (PKVY) is a sub-component of the National Mission for Sustainable "
            "Agriculture that promotes organic farming through a cluster-based approach. Under the scheme, groups "
            "of 50 or more farmers form a cluster covering at least 20 hectares of contiguous or nearby land for "
            "organic farming. Each cluster is supported with Rs 31,000 per hectare over three years for inputs, "
            "certification, and marketing. The scheme has covered over 32,000 clusters across all states, "
            "converting more than 6.5 lakh hectares to certified organic production.\n\n"
            "The scheme supports both PGS-India (Participatory Guarantee System) certification and third-party "
            "certification under NPOP (National Programme for Organic Production). Under PGS-India, farmers in "
            "a cluster collectively guarantee organic practices through mutual trust and peer inspection, making "
            "certification more accessible and affordable. Financial assistance covers organic inputs (Rs 7,500/ha "
            "for bio-fertilizers, bio-pesticides, vermicompost), certification charges, packaging, labelling, "
            "branding (Rs 3,000/ha), and marketing/transportation (Rs 5,000/ha). Farmers also receive training "
            "on organic production practices, composting, and integrated pest management.\n\n"
            "To participate, farmers should contact their district agriculture office or state organic farming "
            "mission. Lead resource persons in each cluster provide technical guidance on organic conversion, "
            "which typically takes 2-3 years for full certification. During the conversion period, farmers can "
            "sell produce as 'in-conversion organic' at a premium over conventional produce. The scheme promotes "
            "linkages with organic markets, Jaivik Kheti portal (jaivikkheti.in), and organic retail chains. "
            "States like Sikkim (100% organic), Uttarakhand, Meghalaya, and Mizoram have made significant "
            "progress under PKVY. The scheme aligns with India's commitment to promote natural and chemical-free "
            "farming on 1 crore hectares by 2028."
        ),
    },
}


def seed_policy_documents():
    table = dynamodb.Table(TABLE_POLICY)
    count = 0
    for doc_id, doc in POLICY_DOCS.items():
        text = doc["text"]
        s3_key = f"policies/{doc_id}.txt"

        # Upload to S3
        print(f"  [policy] Uploading {s3_key} to S3...")
        s3.put_object(
            Bucket=POLICIES_BUCKET,
            Key=s3_key,
            Body=text.encode("utf-8"),
            ContentType="text/plain",
        )

        # Generate embedding via Bedrock Titan Embed v2
        print(f"  [policy] Generating embedding for {doc_id}...")
        response = bedrock.invoke_model(
            modelId="amazon.titan-embed-text-v2:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps({"inputText": text[:8000]}),
        )
        result = json.loads(response["body"].read())
        embedding = result["embedding"]
        embedding_decimal = [Decimal(str(round(v, 8))) for v in embedding]

        # Extract first sentence as summary
        summary = text.split(". ")[0] + "."

        item = {
            "doc_id": doc_id,
            "s3_key": s3_key,
            "title": doc["title"],
            "category": doc["category"],
            "state": "all",
            "language": "en",
            "summary": summary,
            "embedding": embedding_decimal,
            "embedding_status": "completed",
        }
        table.put_item(Item=item)
        count += 1
        print(f"  [policy] Stored {doc_id}: {doc['title']}")
    print(f"  => Inserted {count} policy-document records (DynamoDB + S3).\n")


# ---------------------------------------------------------------------------
# 5. Farmers
# ---------------------------------------------------------------------------

FARMERS = [
    {
        "farmer_id": "farmer-001",
        "name": "Ramesh Kumar",
        "district": "Lucknow",
        "state": "Uttar Pradesh",
        "crops": ["wheat", "rice"],
        "land_acres": Decimal("5"),
        "language": "hi",
    },
    {
        "farmer_id": "farmer-002",
        "name": "Priya Patil",
        "district": "Nashik",
        "state": "Maharashtra",
        "crops": ["onion", "tomato", "grape"],
        "land_acres": Decimal("3"),
        "language": "mr",
    },
    {
        "farmer_id": "farmer-003",
        "name": "Suresh Reddy",
        "district": "Hyderabad",
        "state": "Telangana",
        "crops": ["cotton", "rice", "maize"],
        "land_acres": Decimal("8"),
        "language": "te",
    },
]


def seed_farmers():
    table = dynamodb.Table(TABLE_FARMERS)
    count = 0
    for farmer in FARMERS:
        table.put_item(Item=farmer)
        count += 1
        print(f"  [farmer] {farmer['farmer_id']}: {farmer['name']} ({farmer['district']}, {farmer['state']})")
    print(f"  => Inserted {count} farmer records.\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("Agri-Mitra Seed Data Script")
    print(f"Region: {REGION} | Date: {TODAY}")
    print("=" * 60)

    print("\n[1/5] Seeding mandi prices...")
    seed_mandi_prices()

    print("[2/5] Seeding weather cache...")
    seed_weather()

    print("[3/5] Seeding news...")
    seed_news()

    print("[4/5] Seeding policy documents (S3 + Bedrock embeddings + DynamoDB)...")
    seed_policy_documents()

    print("[5/5] Seeding farmers...")
    seed_farmers()

    print("=" * 60)
    print("Seed data complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
