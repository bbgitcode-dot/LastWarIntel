"""
Sentinel
Server Validator
"""

from __future__ import annotations

from dataclasses import dataclass

from analytics.validation.models import (
    ValidationIssue,
    ValidationResult,
    ValidationStatus,
)
from analytics.validation.ranking_validator import RankingValidator


@dataclass(slots=True, frozen=True)
class ServerValidationInput:
    """
    Input data required for server assessment validation.
    """

    alliance_ranks: list[int]
    thp_ranks: list[int]


class ServerValidator:
    """
    Validates whether a server can be assessed.
    """

    MIN_ALLIANCE_RANKS = 10
    MIN_THP_RANKS = 10

    def __init__(self) -> None:
        self._ranking_validator = RankingValidator()

    def validate(
        self,
        data: ServerValidationInput,
    ) -> ValidationResult:
        alliance_result = self._ranking_validator.validate_minimum_top_ranks(
            ranks=data.alliance_ranks,
            minimum_required=self.MIN_ALLIANCE_RANKS,
            label="Alliance Ranking",
        )

        thp_result = self._ranking_validator.validate_minimum_top_ranks(
            ranks=data.thp_ranks,
            minimum_required=self.MIN_THP_RANKS,
            label="THP Ranking",
        )

        issues: list[ValidationIssue] = []
        issues.extend(alliance_result.issues)
        issues.extend(thp_result.issues)

        quality_score = round(
            (alliance_result.quality_score + thp_result.quality_score) / 2,
            2,
        )

        if alliance_result.status == ValidationStatus.PASSED and thp_result.status == ValidationStatus.PASSED:
            return ValidationResult(
                status=ValidationStatus.PASSED,
                quality_score=quality_score,
                summary="Server assessment dataset is complete.",
            )

        return ValidationResult(
            status=ValidationStatus.FAILED,
            quality_score=quality_score,
            issues=issues,
            summary="Server assessment dataset is incomplete.",
        )