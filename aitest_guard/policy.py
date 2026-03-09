"""Policy loader and configuration."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DEFAULT_POLICY_YAML = """language: python
framework: pytest

# ---------------------------
# UNIT TEST GOVERNANCE
# ---------------------------
unit_tests:
  enforce: true
  ignore_private_functions: true
  enforce_naming: true

  required_scenarios:
    - happy_path
    - invalid_input
    - exception_case

  min_assertions_per_test: 1
  require_pytest_raises_for_exceptions: true
  disallow_empty_tests: true

# ---------------------------
# RISK-BASED TESTING (Optional Tagging Support)
# ---------------------------
risk_classification:
  critical:
    required_scenarios:
      - happy_path
      - boundary_condition
      - invalid_input
      - exception_case
      - edge_case
    min_assertions_per_test: 2

  standard:
    required_scenarios:
      - happy_path
      - invalid_input
      - exception_case

# ---------------------------
# INTEGRATION TEST GOVERNANCE
# ---------------------------
integration_tests:
  enforce: true
  detect_external_calls:
    - requests
    - httpx
    - boto3

  required_scenarios:
    - success_response
    - client_error
    - server_error
    - timeout

  require_mocking: true
  require_status_code_assertion: true

# ---------------------------
# WEAK TEST DETECTION
# ---------------------------
weak_test_detection:
  enabled: true
  patterns:
    - "assert True"
    - "assert False"
    - "assert 1"
    - "assert 0"
    - "assert result is not None"
    - "assert response is not None"

# ---------------------------
# ASSERTION QUALITY POLICY
# ---------------------------
assertion_policy:
  disallow_generic_assertions:
    - "assert result is not None"
    - "assert True"

  require_meaningful_assertion: true

# ---------------------------
# COVERAGE POLICY
# ---------------------------
coverage:
  enabled: true
  minimum: 80
  diff_coverage_minimum: 85
  fail_on_drop: true
  ignore_test_files: true

# ---------------------------
# ENFORCEMENT BEHAVIOR
# ---------------------------
enforcement:
  mode: strict        # strict | warn
  scope: staged       # staged | full_repo | modified | pr
  pr_base: main       # base branch for scope: pr (e.g. main, origin/main)
  block_commit: true
  block_merge: false
  block_release: false
  require_manual_override_for_high: false

# ---------------------------
# LLM CONFIGURATION
# ---------------------------
llm:
  enabled: false
  provider: openai
  model: gpt-4o-mini
  temperature: 0.2
  max_tokens: 1500
  auto_format: true
  require_manual_review: true

# ---------------------------
# AI GENERATION
# ---------------------------
ai_generation:
  enforce_output_validation: true
  reject_on_validation_failure: true

# ---------------------------
# AI OUTPUT GOVERNANCE (Enterprise)
# ---------------------------
ai_output_governance:
  traceability_policy:
    enabled: false
    min_test_case_per_requirement: 1
    violation_weight: 10

  edge_case_policy:
    enabled: false
    min_ratio: 0.2
    violation_weight: 5

  vague_phrase_policy:
    enabled: true
    forbidden_phrases:
      - "assert result is not None"
      - "assert True"
      - "assert False"
    violation_weight: 3

  deterministic_format_policy:
    enabled: true
    required_test_fields:
      - id
      - scenario_type
      - assertions
    violation_weight: 5

# ---------------------------
# RISK SCORING
# ---------------------------
risk_scoring:
  weights:
    MISSING_TRACEABILITY: 10
    LOW_EDGE_COVERAGE: 5
    VAGUE_ASSERTION: 3
    FORMAT_VIOLATION: 5
    MISSING_SCENARIO: 8
    WEAK_ASSERTION: 3
    NO_ASSERTIONS: 5
    MISSING_SECURITY_TESTS: 15
    AMBIGUOUS_REQUIREMENT: 8
    MISSING_ERROR_SPECIFICATION: 8
    CONTRACT_VERSION_MISMATCH: 10
  thresholds:
    low_max: 10
    medium_max: 50

# ---------------------------
# RISK CONTEXT (Enterprise v2)
# ---------------------------
risk_context:
  module_multipliers:
    billing: 2.0
    auth: 2.0
    payment: 2.5
  classification_multipliers:
    critical: 2.0
    standard: 1.0

# ---------------------------
# SECURITY GOVERNANCE
# ---------------------------
security_governance:
  enabled: false
  required_security_scenarios:
    - auth_negative
    - permission_denied
    - input_validation
    - injection_attempt
  violation_weight: 15

# ---------------------------
# REQUIREMENT GOVERNANCE
# ---------------------------
requirement_governance:
  enabled: false
  detect_ambiguity_keywords:
    - should
    - may
    - etc
    - "as needed"
  require_explicit_error_message: true
  violation_weight: 8

# ---------------------------
# AUDIT
# ---------------------------
audit:
  enabled: true
  retention_days: 90
  include_artifact_snapshot: false
  include_risk_score: true

# ---------------------------
# OUTPUT CONTRACT
# ---------------------------
output_contract:
  version: 1.0
  enforce_version_match: false

# ---------------------------
# LLM GOVERNANCE (Optional Intelligence Layer)
# ---------------------------
llm_governance:
  enabled: false
  mode: advisory   # advisory | scoring | blocking
  max_repo_tokens: 50000
  semantic_quality_weight: 5
  confidence_threshold: 0.5
  architecture_analysis: true
  concurrency_detection: true
  detect_mock_abuse: true
"""


@dataclass
class Policy:
    """Loaded policy configuration."""

    language: str
    framework: str
    # unit_tests
    enforce: bool
    required_scenarios: list[str]
    enforce_naming: bool
    require_docstring: bool
    ignore_private_functions: bool
    min_assertions_per_test: int
    require_pytest_raises_for_exceptions: bool
    disallow_empty_tests: bool
    # risk_classification
    risk_classification: dict[str, dict[str, Any]]
    # integration_tests
    integration_enabled: bool
    integration_scenarios: list[str]
    integration_enforce_naming: bool
    integration_require_docstring: bool
    integration_detect_external_calls: list[str]
    integration_require_mocking: bool
    integration_require_status_code_assertion: bool
    # weak_test_detection
    weak_detection_enabled: bool
    weak_detection_patterns: list[str]
    # assertion_policy
    disallow_generic_assertions: list[str]
    require_meaningful_assertion: bool
    # coverage
    coverage_enabled: bool
    coverage_minimum: int
    diff_coverage_minimum: int
    fail_on_drop: bool
    ignore_test_files: bool
    # llm
    llm_enabled: bool
    llm_provider: str
    llm_model: str
    llm_temperature: float
    llm_max_tokens: int
    llm_auto_format: bool
    llm_require_manual_review: bool
    # ai_generation
    ai_enforce_output_validation: bool
    ai_reject_on_validation_failure: bool
    # enforcement
    enforcement_mode: str
    enforcement_scope: str
    enforcement_pr_base: str
    block_commit: bool
    # llm_governance (optional intelligence layer)
    llm_governance_enabled: bool
    llm_governance_mode: str
    llm_governance_max_repo_tokens: int
    llm_governance_semantic_quality_weight: float
    llm_governance_confidence_threshold: float
    llm_governance_architecture_analysis: bool
    llm_governance_concurrency_detection: bool
    llm_governance_detect_mock_abuse: bool


DEFAULT_SCENARIOS = ["happy_path", "invalid_input", "exception_case"]
DEFAULT_INTEGRATION_SCENARIOS = [
    "success_response",
    "client_error",
    "server_error",
    "timeout",
]


def _get_risk_scenarios(
    risk_classification: dict[str, Any], level: str
) -> list[str]:
    """Get required scenarios for a risk level. Fallback to default if not found."""
    level_config = risk_classification.get(level, {})
    return level_config.get("required_scenarios", DEFAULT_SCENARIOS)


def _get_risk_min_assertions(
    risk_classification: dict[str, Any], level: str, default: int
) -> int:
    """Get min_assertions for a risk level."""
    level_config = risk_classification.get(level, {})
    return level_config.get("min_assertions_per_test", default)


def load_policy(config_dir: Path) -> Policy | None:
    """Load policy from .aitest/policy.yaml. Returns None if not found."""
    policy_path = config_dir / "policy.yaml"
    if not policy_path.exists():
        return None

    with open(policy_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    unit = data.get("unit_tests", {})
    risk = data.get("risk_classification", {})
    integration = data.get("integration_tests", {})
    weak = data.get("weak_test_detection", {})
    assertion = data.get("assertion_policy", {})
    coverage = data.get("coverage", {})
    llm = data.get("llm", {})
    ai_gen = data.get("ai_generation", {})
    enforcement = data.get("enforcement", {})
    llm_gov = data.get("llm_governance", {})

    return Policy(
        language=data.get("language", "python"),
        framework=data.get("framework", "pytest"),
        # unit_tests
        enforce=unit.get("enforce", True),
        required_scenarios=unit.get("required_scenarios", DEFAULT_SCENARIOS),
        enforce_naming=unit.get("enforce_naming", True),
        require_docstring=unit.get("require_docstring", False),
        ignore_private_functions=unit.get("ignore_private_functions", True),
        min_assertions_per_test=int(unit.get("min_assertions_per_test", 1)),
        require_pytest_raises_for_exceptions=unit.get(
            "require_pytest_raises_for_exceptions", True
        ),
        disallow_empty_tests=unit.get("disallow_empty_tests", True),
        # risk_classification
        risk_classification=risk,
        # integration_tests
        integration_enabled=integration.get(
            "enforce", integration.get("enabled", False)
        ),
        integration_scenarios=integration.get(
            "required_scenarios", DEFAULT_INTEGRATION_SCENARIOS
        ),
        integration_enforce_naming=integration.get("enforce_naming", True),
        integration_require_docstring=integration.get("require_docstring", False),
        integration_detect_external_calls=integration.get(
            "detect_external_calls", []
        ),
        integration_require_mocking=integration.get("require_mocking", False),
        integration_require_status_code_assertion=integration.get(
            "require_status_code_assertion", True
        ),
        # weak_test_detection
        weak_detection_enabled=weak.get("enabled", False),
        weak_detection_patterns=weak.get("patterns", []),
        # assertion_policy
        disallow_generic_assertions=assertion.get(
            "disallow_generic_assertions", []
        ),
        require_meaningful_assertion=assertion.get(
            "require_meaningful_assertion", False
        ),
        # coverage
        coverage_enabled=coverage.get("enabled", False),
        coverage_minimum=coverage.get("minimum", 80),
        diff_coverage_minimum=coverage.get("diff_coverage_minimum", 85),
        fail_on_drop=coverage.get("fail_on_drop", True),
        ignore_test_files=coverage.get("ignore_test_files", True),
        # llm
        llm_enabled=llm.get("enabled", False),
        llm_provider=llm.get("provider", "openai"),
        llm_model=llm.get("model", "gpt-4o-mini"),
        llm_temperature=float(llm.get("temperature", 0.2)),
        llm_max_tokens=int(llm.get("max_tokens", 1500)),
        llm_auto_format=llm.get("auto_format", True),
        llm_require_manual_review=llm.get("require_manual_review", False),
        # ai_generation
        ai_enforce_output_validation=ai_gen.get("enforce_output_validation", True),
        ai_reject_on_validation_failure=ai_gen.get("reject_on_validation_failure", True),
        # enforcement
        enforcement_mode=enforcement.get("mode", "strict"),
        enforcement_scope=enforcement.get("scope", "staged"),
        enforcement_pr_base=enforcement.get("pr_base", "main"),
        block_commit=enforcement.get("block_commit", True),
        # llm_governance
        llm_governance_enabled=llm_gov.get("enabled", False),
        llm_governance_mode=llm_gov.get("mode", "advisory"),
        llm_governance_max_repo_tokens=int(llm_gov.get("max_repo_tokens", 50000)),
        llm_governance_semantic_quality_weight=float(
            llm_gov.get("semantic_quality_weight", 5)
        ),
        llm_governance_confidence_threshold=float(
            llm_gov.get("confidence_threshold", 0.5)
        ),
        llm_governance_architecture_analysis=llm_gov.get("architecture_analysis", True),
        llm_governance_concurrency_detection=llm_gov.get("concurrency_detection", True),
        llm_governance_detect_mock_abuse=llm_gov.get("detect_mock_abuse", True),
    )


def load_policy_dict(config_dir: Path) -> dict | None:
    """Load raw policy as dict for governance layer. Returns None if not found."""
    policy_path = config_dir / "policy.yaml"
    if not policy_path.exists():
        return None
    with open(policy_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_config_dir(project_root: Path | None = None) -> Path:
    """Return .aitest config directory path."""
    root = project_root or Path.cwd()
    return root / ".aitest"


def write_default_policy(config_dir: Path) -> None:
    """Create config dir and write default policy.yaml."""
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "policy.yaml").write_text(DEFAULT_POLICY_YAML, encoding="utf-8")
