"""Validator module for aitest-guard enforcement demo."""

import re


def validate_email(email: str) -> bool:
    """Check if string looks like a valid email."""
    if not email or not isinstance(email, str):
        return False
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email.strip()))
