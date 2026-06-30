"""Repository boundary for operational data quality.

Application code depends on this protocol instead of concrete files such as
validator JSON reports.  Ground truth remains a development/benchmark concern;
runtime services consume operational quality reports through this boundary.
"""

from __future__ import annotations

from typing import Any, Protocol


class QualityReportRepository(Protocol):
    """Load the latest operational quality report from the runtime source."""

    def load_latest_report(self) -> dict[str, Any] | None:
        """Return the latest report payload, or ``None`` if no report exists."""
        ...

    def describe_source(self) -> str:
        """Return a user-facing source description for diagnostics."""
        ...
