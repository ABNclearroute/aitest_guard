"""Violation model for governance validation."""

from dataclasses import dataclass
from enum import Enum


class ViolationCode(str, Enum):
    """Standard violation codes for governance."""

    MISSING_TRACEABILITY = "MISSING_TRACEABILITY"
    LOW_EDGE_COVERAGE = "LOW_EDGE_COVERAGE"
    VAGUE_ASSERTION = "VAGUE_ASSERTION"
    FORMAT_VIOLATION = "FORMAT_VIOLATION"
    MISSING_SCENARIO = "MISSING_SCENARIO"
    WEAK_ASSERTION = "WEAK_ASSERTION"
    NO_ASSERTIONS = "NO_ASSERTIONS"
    GENERIC_ASSERTION = "GENERIC_ASSERTION"
    MISSING_SECURITY_TESTS = "MISSING_SECURITY_TESTS"
    AMBIGUOUS_REQUIREMENT = "AMBIGUOUS_REQUIREMENT"
    MISSING_ERROR_SPECIFICATION = "MISSING_ERROR_SPECIFICATION"
    CONTRACT_VERSION_MISMATCH = "CONTRACT_VERSION_MISMATCH"


@dataclass
class Violation:
    """A single governance violation."""

    code: ViolationCode
    message: str
    context: str | None = None
    weight: int = 1
    module: str | None = None
    risk_tag: str | None = None
