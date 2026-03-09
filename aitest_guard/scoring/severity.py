"""Risk level and severity types."""

from enum import Enum


class RiskLevel(str, Enum):
    """Risk level for compliance result."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
