"""
Sentinel
Validation Models
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ValidationStatus(Enum):
    PASSED = "Passed"
    WARNING = "Warning"
    FAILED = "Failed"


@dataclass(slots=True, frozen=True)
class ValidationIssue:
    """
    One validation issue.
    """

    title: str
    description: str
    status: ValidationStatus


@dataclass(slots=True, frozen=True)
class ValidationResult:
    """
    Result of a validation check.
    """

    status: ValidationStatus

    quality_score: float

    issues: list[ValidationIssue] = field(default_factory=list)

    summary: str = ""