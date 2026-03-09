"""Artifact model: structured representation of parsed test code."""

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aitest_guard.models.requirement_model import Requirement
from aitest_guard.models.test_case_model import TestCase, ScenarioType

KNOWN_SCENARIOS: frozenset[str] = frozenset({
    "happy_path", "invalid_input", "edge_case", "exception_case", "boundary_condition",
    "success_response", "client_error", "server_error", "timeout", "empty_input",
    "auth_negative", "permission_denied", "input_validation", "injection_attempt",
})


def _extract_scenario_type(test_name: str) -> ScenarioType:
    """Infer scenario type from test_<func>_<scenario> naming. Match scenario from end."""
    if not test_name.startswith("test_"):
        return "unknown"
    for scenario in KNOWN_SCENARIOS:
        if scenario == "unknown":
            continue
        suffix = "_" + scenario
        if test_name.endswith(suffix):
            return scenario  # type: ignore
    return "unknown"


def _extract_assertions_from_node(node: ast.FunctionDef, source: str) -> list[str]:
    """Extract assertion text from function body."""
    assertions: list[str] = []
    for n in ast.walk(node):
        if isinstance(n, ast.Assert) and hasattr(n, "lineno"):
            lines = source.split("\n")
            idx = n.lineno - 1
            if 0 <= idx < len(lines):
                assertions.append(lines[idx].strip())
    return assertions


def _get_risk_from_docstring(node: ast.FunctionDef) -> str:
    """Infer risk tag from docstring."""
    doc = ast.get_docstring(node)
    if not doc:
        return "standard"
    if "critical" in doc.lower() or "aitest: critical" in doc.lower():
        return "critical"
    return "standard"


def _extract_contract_version(source_code: str) -> str | None:
    """Extract aitest_contract_version from comment or assignment in source."""
    for line in source_code.split("\n")[:30]:
        line = line.strip()
        if "# aitest_contract_version:" in line:
            parts = line.split(":", 1)
            if len(parts) == 2:
                return parts[1].strip().strip('"\'')
        if "aitest_contract_version" in line and "=" in line:
            match = re.search(r'["\']([^"\']+)["\']', line)
            if match:
                return match.group(1)
    return None


def parse_python_test_artifact(
    source_code: str,
    artifact_id: str = "default",
    source_module: str = "",
) -> "Artifact":
    """
    Parse Python test code into structured Artifact.
    Extracts test_<func>_<scenario> functions, infers requirements from func names.
    """
    contract_version = _extract_contract_version(source_code)
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return Artifact(
            artifact_id=artifact_id,
            requirements=[],
            test_cases=[],
            traceability_matrix={},
            source_module=source_module,
            contract_version=contract_version,
        )

    test_cases: list[TestCase] = []
    func_to_tests: dict[str, list[str]] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            scenario = _extract_scenario_type(node.name)
            assertions = _extract_assertions_from_node(node, source_code)
            risk = _get_risk_from_docstring(node)
            tc = TestCase(
                id=node.name,
                scenario_type=scenario if scenario in KNOWN_SCENARIOS else "unknown",
                assertions=assertions,
                module=source_module,
                risk_tag=risk if risk in ("critical", "standard", "optional") else "standard",
            )
            test_cases.append(tc)
            if scenario != "unknown":
                prefix = "test_"
                suffix = "_" + scenario
                if node.name.startswith(prefix) and node.name.endswith(suffix):
                    func_part = node.name[len(prefix): -len(suffix)]
                    if func_part:
                        func_to_tests.setdefault(func_part, []).append(node.name)

    requirements = [
        Requirement(id=rid, description=f"Requirement for {rid}")
        for rid in func_to_tests
    ]
    traceability_matrix = {rid: tids for rid, tids in func_to_tests.items()}

    return Artifact(
        artifact_id=artifact_id,
        requirements=requirements,
        test_cases=test_cases,
        traceability_matrix=traceability_matrix,
        source_module=source_module,
        contract_version=contract_version,
    )


def parse_artifact_from_file(path: Path, artifact_id: str = "") -> "Artifact":
    """Parse a test file into Artifact."""
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        source = ""
    aid = artifact_id or str(path)
    return parse_python_test_artifact(source, artifact_id=aid, source_module=str(path.stem))


@dataclass
class Artifact:
    """Parsed artifact from AI-generated or existing test code."""

    artifact_id: str
    requirements: list[Requirement]
    test_cases: list[TestCase]
    traceability_matrix: dict[str, list[str]]
    source_module: str = ""
    contract_version: str | None = None
