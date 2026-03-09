"""Requirement model for traceability."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Requirement:
    """A requirement that tests must trace to."""

    id: str
    description: str
