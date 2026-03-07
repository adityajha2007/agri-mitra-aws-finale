"""Deterministic agricultural calculator tool."""

import logging

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Average yield data (quintals per acre) for common Indian crops
CROP_YIELDS = {
    "wheat": 12.0,
    "rice": 15.0,
    "maize": 10.0,
    "cotton": 5.0,
    "sugarcane": 250.0,
    "soybean": 6.0,
    "mustard": 5.5,
    "potato": 80.0,
    "onion": 60.0,
    "tomato": 80.0,
    "chana": 5.5,
    "bajra": 7.0,
    "jowar": 6.0,
    "groundnut": 7.0,
}


@tool
def calculate(
    calculation_type: str,
    crop: str = "",
    land_acres: float = 0,
    price_per_quintal: float = 0,
    cost_per_acre: float = 0,
    quantity_quintals: float = 0,
    prices: str = "",
) -> str:
    """Perform agricultural calculations for yield, cost, profit, and market comparison.

    Use this tool when the farmer needs to calculate expected yields, farming costs,
    profit margins, or compare prices across markets.

    Args:
        calculation_type: Type of calculation — 'yield', 'profit', 'cost', 'best_market'
        crop: Crop name for yield lookups
        land_acres: Land area in acres
        price_per_quintal: Selling price per quintal (₹)
        cost_per_acre: Total input cost per acre (₹)
        quantity_quintals: Quantity in quintals (for profit calc)
        prices: Comma-separated 'market:price' pairs for best_market (e.g., 'Azadpur:2500,Vashi:2600')

    Returns:
        Calculation result with methodology explanation
    """
    try:
        calc = calculation_type.lower().strip()

        if calc == "yield":
            return _calc_yield(crop, land_acres)
        elif calc == "profit":
            return _calc_profit(crop, land_acres, price_per_quintal, cost_per_acre, quantity_quintals)
        elif calc == "cost":
            return _calc_cost(cost_per_acre, land_acres)
        elif calc == "best_market":
            return _calc_best_market(prices, quantity_quintals)
        else:
            return (
                f"Unknown calculation type: '{calculation_type}'. "
                "Supported types: 'yield', 'profit', 'cost', 'best_market'"
            )
    except Exception as e:
        logger.error("Calculation error: %s", e)
        return f"Calculation error: {str(e)}"


def _calc_yield(crop: str, land_acres: float) -> str:
    crop_lower = crop.lower().strip()
    avg_yield = CROP_YIELDS.get(crop_lower)

    if not avg_yield:
        return (
            f"Yield data not available for '{crop}'. "
            f"Available crops: {', '.join(sorted(CROP_YIELDS.keys()))}"
        )
    if land_acres <= 0:
        return "Please provide a valid land area in acres (must be > 0)."

    total = avg_yield * land_acres
    return (
        f"**Expected Yield for {crop.title()}**\n"
        f"- Land area: {land_acres} acres\n"
        f"- Average yield: {avg_yield} quintals/acre\n"
        f"- **Expected total yield: {total:.1f} quintals**\n\n"
        f"*Note: Actual yield varies with soil quality, weather, seeds, and farming practices.*"
    )


def _calc_profit(
    crop: str, land_acres: float, price: float, cost: float, quantity: float
) -> str:
    if quantity <= 0 and land_acres > 0 and crop:
        avg_yield = CROP_YIELDS.get(crop.lower().strip(), 0)
        if avg_yield:
            quantity = avg_yield * land_acres

    if quantity <= 0:
        return "Please provide quantity in quintals or both crop name and land area."
    if price <= 0:
        return "Please provide the selling price per quintal."

    revenue = price * quantity
    total_cost = cost * land_acres if cost > 0 and land_acres > 0 else 0
    profit = revenue - total_cost

    lines = [
        f"**Profit Calculation**\n",
        f"- Quantity: {quantity:.1f} quintals",
        f"- Price: ₹{price:,.0f}/quintal",
        f"- **Revenue: ₹{revenue:,.0f}**",
    ]
    if total_cost > 0:
        lines.extend([
            f"- Cost: ₹{cost:,.0f}/acre × {land_acres} acres = ₹{total_cost:,.0f}",
            f"- **Net Profit: ₹{profit:,.0f}**",
            f"- Profit Margin: {(profit / revenue * 100):.1f}%",
        ])

    return "\n".join(lines)


def _calc_cost(cost_per_acre: float, land_acres: float) -> str:
    if cost_per_acre <= 0 or land_acres <= 0:
        return "Please provide both cost per acre and land area."

    total = cost_per_acre * land_acres
    return (
        f"**Cost Calculation**\n"
        f"- Cost per acre: ₹{cost_per_acre:,.0f}\n"
        f"- Land area: {land_acres} acres\n"
        f"- **Total cost: ₹{total:,.0f}**"
    )


def _calc_best_market(prices_str: str, quantity: float) -> str:
    if not prices_str:
        return "Please provide market:price pairs (e.g., 'Azadpur:2500,Vashi:2600')."

    markets = {}
    for pair in prices_str.split(","):
        pair = pair.strip()
        if ":" in pair:
            name, price = pair.rsplit(":", 1)
            try:
                markets[name.strip()] = float(price.strip())
            except ValueError:
                continue

    if not markets:
        return "Could not parse market prices. Use format: 'Market1:Price1,Market2:Price2'"

    best = max(markets, key=markets.get)  # type: ignore[arg-type]
    lines = [f"**Market Price Comparison**\n"]
    for name, price in sorted(markets.items(), key=lambda x: x[1], reverse=True):
        marker = " ← Best" if name == best else ""
        line = f"- {name}: ₹{price:,.0f}/quintal{marker}"
        if quantity > 0:
            line += f" (Revenue: ₹{price * quantity:,.0f})"
        lines.append(line)

    if quantity > 0:
        diff = (markets[best] - min(markets.values())) * quantity
        lines.append(f"\nSelling at {best} earns ₹{diff:,.0f} more than the cheapest market.")

    return "\n".join(lines)
