"""Operational quality repository adapters.

This module intentionally owns the current compatibility adapter that reads the
validator JSON output.  The Command Center and application services do not know
or care whether data comes from JSON, SQLite, or a future PostgreSQL backend.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonQualityReportRepository:
    """Compatibility repository for the latest validator report.

    The JSON file is treated as an adapter input, not as an application/runtime
    dependency.  This keeps the UI and application layer independent from the
    ground-truth validator while preserving the current workflow.
    """

    def __init__(self, report_path: Path | str | None = None) -> None:
        self._report_path = Path(report_path or "benchmarks/ground_truth_validation_report.json")

    def load_latest_report(self) -> dict[str, Any] | None:
        if not self._report_path.exists():
            return None
        try:
            with self._report_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    def describe_source(self) -> str:
        return str(self._report_path)
