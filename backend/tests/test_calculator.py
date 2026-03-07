"""Tests for the calculator tool."""

import pytest
from app.tools.calculator import calculate


class TestYieldCalculation:
    def test_wheat_yield(self):
        result = calculate.invoke({
            "calculation_type": "yield",
            "crop": "wheat",
            "land_acres": 5,
        })
        assert "60.0 quintals" in result
        assert "wheat" in result.lower()

    def test_rice_yield(self):
        result = calculate.invoke({
            "calculation_type": "yield",
            "crop": "rice",
            "land_acres": 3,
        })
        assert "45.0 quintals" in result

    def test_unknown_crop(self):
        result = calculate.invoke({
            "calculation_type": "yield",
            "crop": "dragonfruit",
            "land_acres": 5,
        })
        assert "not available" in result.lower()

    def test_zero_acres(self):
        result = calculate.invoke({
            "calculation_type": "yield",
            "crop": "wheat",
            "land_acres": 0,
        })
        assert "valid land area" in result.lower()


class TestProfitCalculation:
    def test_basic_profit(self):
        result = calculate.invoke({
            "calculation_type": "profit",
            "crop": "",
            "quantity_quintals": 60,
            "price_per_quintal": 2500,
            "cost_per_acre": 0,
            "land_acres": 0,
        })
        assert "1,50,000" in result or "150,000" in result

    def test_profit_with_cost(self):
        result = calculate.invoke({
            "calculation_type": "profit",
            "crop": "",
            "quantity_quintals": 60,
            "price_per_quintal": 2500,
            "cost_per_acre": 10000,
            "land_acres": 5,
        })
        assert "Net Profit" in result

    def test_auto_yield_estimation(self):
        result = calculate.invoke({
            "calculation_type": "profit",
            "crop": "wheat",
            "land_acres": 5,
            "price_per_quintal": 2500,
            "cost_per_acre": 0,
            "quantity_quintals": 0,
        })
        assert "60.0 quintals" in result


class TestBestMarket:
    def test_compare_markets(self):
        result = calculate.invoke({
            "calculation_type": "best_market",
            "prices": "Azadpur:2500,Vashi:2600,Pune:2400",
            "quantity_quintals": 10,
        })
        assert "Vashi" in result
        assert "Best" in result

    def test_empty_prices(self):
        result = calculate.invoke({
            "calculation_type": "best_market",
            "prices": "",
            "quantity_quintals": 0,
        })
        assert "provide" in result.lower()


class TestCostCalculation:
    def test_basic_cost(self):
        result = calculate.invoke({
            "calculation_type": "cost",
            "cost_per_acre": 10000,
            "land_acres": 5,
        })
        assert "50,000" in result

    def test_invalid_params(self):
        result = calculate.invoke({
            "calculation_type": "cost",
            "cost_per_acre": 0,
            "land_acres": 0,
        })
        assert "provide" in result.lower()


class TestUnknownType:
    def test_unknown_calculation_type(self):
        result = calculate.invoke({
            "calculation_type": "unknown",
        })
        assert "Unknown calculation type" in result
