"""Tests for example_api.calculator."""

import pytest

from example_api.calculator import calculate_total


def test_calculate_total_happy_path() -> None:
    """Sum of numeric items."""
    result = calculate_total([1.0, 2.0, 3.0])
    assert result == 6.0


def test_calculate_total_invalid_input() -> None:
    """Empty list returns 0."""
    result = calculate_total([])
    assert result == 0.0


def test_calculate_total_exception_case() -> None:
    """Non-numeric item raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        calculate_total([1, 2, "not_a_number"])
    assert "could not convert" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()
