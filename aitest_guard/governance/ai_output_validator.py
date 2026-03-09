"""AI Output Governance Layer: parsing, validation, scoring, and audit."""

from pathlib import Path
from typing import Any, Protocol

from aitest_guard.engine.validator_registry import run_governance
from aitest_guard.models.artifact_model import Artifact, parse_artifact_from_file


class LLMProviderProtocol(Protocol):
    def generate(self, prompt: str) -> str:
        ...


def validate_artifact_governance(
    artifact: Artifact,
    policy: dict[str, Any],
    policy_name: str = "default",
    enforcement_mode: str = "strict",
    llm_provider: LLMProviderProtocol | None = None,
    test_source: str = "",
    source_code: str = "",
) -> dict[str, Any]:
    """
    Run full governance validation on a structured artifact.
    Returns compliance result contract.
    """
    return run_governance(
        artifact=artifact,
        policy=policy,
        policy_name=policy_name,
        enforcement_mode=enforcement_mode,
        llm_provider=llm_provider,
        test_source=test_source,
        source_code=source_code,
    )


def validate_file_governance(
    test_file_path: Path,
    policy: dict[str, Any],
    policy_name: str = "default",
    enforcement_mode: str = "strict",
    llm_provider: LLMProviderProtocol | None = None,
    source_code: str = "",
) -> dict[str, Any]:
    """
    Parse test file to Artifact and run governance.
    Returns compliance result contract.
    """
    try:
        test_source = test_file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        test_source = ""
    artifact = parse_artifact_from_file(test_file_path, artifact_id=str(test_file_path))
    return validate_artifact_governance(
        artifact=artifact,
        policy=policy,
        policy_name=policy_name,
        enforcement_mode=enforcement_mode,
        llm_provider=llm_provider,
        test_source=test_source,
        source_code=source_code,
    )
