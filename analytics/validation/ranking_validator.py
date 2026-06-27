"""
Sentinel
Ranking Validator
"""

from __future__ import annotations

from analytics.validation.models import (
    ValidationIssue,
    ValidationResult,
    ValidationStatus,
)


class RankingValidator:
    """
    Validates ranking completeness.
    """

    def validate_minimum_top_ranks(
        self,
        ranks: list[int],
        minimum_required: int,
        label: str,
    ) -> ValidationResult:
        expected = set(range(1, minimum_required + 1))
        found = set(ranks)

        missing = sorted(expected - found)

        if not missing:
            return ValidationResult(
                status=ValidationStatus.PASSED,
                quality_score=100.0,
                summary=f"{label} contains required Top {minimum_required}.",
            )

        found_required = minimum_required - len(missing)

        quality_score = max(
            0.0,
            round((found_required / minimum_required) * 100, 2),
        )

        return ValidationResult(
            status=ValidationStatus.FAILED,
            quality_score=quality_score,
            issues=[
                ValidationIssue(
                    title=f"Incomplete {label}",
                    description=(
                        f"Missing required ranks: "
                        f"{', '.join(str(rank) for rank in missing)}"
                    ),
                    status=ValidationStatus.FAILED,
                )
            ],
            summary=(
                f"{label} is incomplete. "
                f"Found {found_required}/{minimum_required} required ranks."
            ),
        )