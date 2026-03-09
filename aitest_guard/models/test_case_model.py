"""TestCase model for structured artifact parsing."""

from dataclasses import dataclass
from typing import Literal

ScenarioType = Literal[
    "happy_path",
    "invalid_input",
    "edge_case",
    "exception_case",
    "boundary_condition",
    "empty_input",
    "success_response",
    "client_error",
    "server_error",
    "timeout",
    "auth_negative",
    "permission_denied",
    "input_validation",
    "injection_attempt",
    "unknown",
]

RiskTag = Literal["critical", "standard", "optional"]


@dataclass
class TestCase:
    """A parsed test case from AI-generated or existing test code."""

    id: str
    scenario_type: ScenarioType
    assertions: list[str]
    module: str
    risk_tag: RiskTag = "standard"
