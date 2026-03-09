"""Tests for example_api.validator."""

import pytest

from example_api.validator import validate_email


def test_validate_email_happy_path() -> None:
    """Valid email returns True."""
    result = validate_email("test@example.com")
    assert result is True


def test_validate_email_invalid_input() -> None:
    """Invalid or empty input returns False."""
    assert validate_email("") is False
    assert validate_email("not-an-email") is False


def test_validate_email_exception_case() -> None:
    """String-like object that raises on strip triggers exception path."""

    class BadStr(str):
        def strip(self):
            raise ValueError("strip not supported")

    with pytest.raises(ValueError) as exc_info:
        validate_email(BadStr("test@example.com"))
    assert "strip" in str(exc_info.value).lower()
