"""Base validator for governance layer."""

from abc import ABC, abstractmethod
from typing import Any

from aitest_guard.models.artifact_model import Artifact
from aitest_guard.models.violation_model import Violation


class BaseValidator(ABC):
    """Base class for governance validators. Validators return Violation objects, never print/log."""

    @abstractmethod
    def validate(self, artifact: Artifact, policy: dict[str, Any]) -> list[Violation]:
        """Validate artifact against policy. Returns list of violations (empty = pass)."""
        pass
