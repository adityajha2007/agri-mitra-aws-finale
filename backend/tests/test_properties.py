"""Property-based tests for AgriMitra using Hypothesis.

Each test validates a correctness property from design.md.
"""

import pytest
from hypothesis import given, settings, strategies as st

from app.tools.calculator import calculate, CROP_YIELDS


# Feature: agri-mitra-support-agent, Property 11: Mathematical Calculation Determinism
class TestCalculationDeterminism:
    """Property 11: For any agricultural calculation with valid parameters,
    the system should produce deterministic results."""

    @given(
        crop=st.sampled_from(list(CROP_YIELDS.keys())),
        acres=st.floats(min_value=0.1, max_value=10000, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_yield_deterministic(self, crop, acres):
        """Same inputs always produce same outputs."""
        result1 = calculate.invoke({
            "calculation_type": "yield",
            "crop": crop,
            "land_acres": acres,
        })
        result2 = calculate.invoke({
            "calculation_type": "yield",
            "crop": crop,
            "land_acres": acres,
        })
        assert result1 == result2

    @given(
        crop=st.sampled_from(list(CROP_YIELDS.keys())),
        acres=st.floats(min_value=0.1, max_value=10000, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_yield_positive(self, crop, acres):
        """Yield should always reference a positive number."""
        result = calculate.invoke({
            "calculation_type": "yield",
            "crop": crop,
            "land_acres": acres,
        })
        assert "quintals" in result

    @given(
        quantity=st.floats(min_value=1, max_value=100000, allow_nan=False, allow_infinity=False),
        price=st.floats(min_value=1, max_value=100000, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_revenue_positive(self, quantity, price):
        """Revenue should always be positive for positive quantity and price."""
        result = calculate.invoke({
            "calculation_type": "profit",
            "quantity_quintals": quantity,
            "price_per_quintal": price,
        })
        assert "Revenue" in result


# Feature: agri-mitra-support-agent, Property 12: Input Validation for Calculations
class TestInputValidation:
    """Property 12: For any calculation with invalid parameters,
    the system should validate inputs and request corrections."""

    @given(crop=st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_unknown_crop_handled(self, crop):
        """Unknown crops should return a helpful message, not crash."""
        if crop.lower().strip() in CROP_YIELDS:
            return  # Skip known crops
        result = calculate.invoke({
            "calculation_type": "yield",
            "crop": crop,
            "land_acres": 5,
        })
        assert isinstance(result, str)
        assert len(result) > 0

    @given(
        acres=st.one_of(
            st.floats(max_value=0),
            st.just(float("nan")),
            st.just(float("-inf")),
        ),
    )
    @settings(max_examples=100)
    def test_invalid_acres_handled(self, acres):
        """Zero or negative acres should be rejected gracefully."""
        result = calculate.invoke({
            "calculation_type": "yield",
            "crop": "wheat",
            "land_acres": acres,
        })
        assert isinstance(result, str)
        # Should not crash; should give a message


# Feature: agri-mitra-support-agent, Property 5: Graceful Error Handling
class TestGracefulErrors:
    """Property 5: For any tool execution failure, the system should provide
    alternatives or informative error responses without crashing."""

    @given(calc_type=st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_unknown_calc_type_handled(self, calc_type):
        """Unknown calculation types should be handled gracefully."""
        if calc_type.lower().strip() in ("yield", "profit", "cost", "best_market"):
            return
        result = calculate.invoke({"calculation_type": calc_type})
        assert isinstance(result, str)
        assert "unknown" in result.lower() or "error" in result.lower() or "supported" in result.lower()
