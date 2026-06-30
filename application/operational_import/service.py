"""Application service for the latest operational import run."""

from __future__ import annotations

from typing import Any

from services.import_repository import JsonImportRunRepository

from .models import (
    DataGuardStatusView,
    ImportReviewView,
    OperationalImportDashboard,
    ServerImportView,
)


class OperationalImportService:
    def __init__(self, repository: JsonImportRunRepository | None = None) -> None:
        self._repository = repository or JsonImportRunRepository()

    def get_dashboard(self) -> OperationalImportDashboard:
        payload = self._repository.load_latest_import()
        if not payload:
            return OperationalImportDashboard(
                has_import=False,
                source=self._repository.describe_source(),
                recent_operations=[
                    {
                        "time": "next",
                        "title": "No import run found",
                        "detail": "Run main.py to publish the latest operational import report.",
                        "severity": "warning",
                    }
                ],
            )

        imports = [
            ServerImportView(
                source=str(item.get("source") or ""),
                server=self._optional_int(item.get("server")),
                ranking_type=self._format_ranking_type(str(item.get("ranking_type") or "unknown")),
                rows=self._int(item.get("rows")),
                status=str(item.get("status") or "Unknown"),
                confidence=self._int(item.get("confidence")),
                review_count=self._int(item.get("review_count")),
                screenshots=self._int(item.get("screenshots")),
            )
            for item in payload.get("imports", [])
            if isinstance(item, dict)
        ]
        reviews = [
            ImportReviewView(
                server=self._optional_int(item.get("server")),
                rank=self._optional_int(item.get("rank")),
                title=str(item.get("title") or "Import review"),
                description=str(item.get("description") or "Review required."),
                severity=str(item.get("severity") or "warning"),
                action=str(item.get("action") or "Review import"),
                reason=str(item.get("reason") or "import_review"),
                screenshot=str(item.get("screenshot") or ""),
            )
            for item in payload.get("reviews", [])
            if isinstance(item, dict)
        ]
        guard = payload.get("data_guard", {}) if isinstance(payload.get("data_guard"), dict) else {}
        return OperationalImportDashboard(
            has_import=True,
            source=self._repository.describe_source(),
            created_at=str(payload.get("created_at") or ""),
            runtime_seconds=float(payload.get("runtime_seconds") or 0.0),
            screenshots=self._int(payload.get("screenshots")),
            server_count=self._int(payload.get("server_count")),
            rows=self._int(payload.get("rows")),
            status=str(payload.get("status") or "Unknown"),
            readiness=self._int(payload.get("readiness")),
            review_count=self._int(payload.get("review_count")),
            output_file=str(payload.get("output_file") or ""),
            servers=[self._int(value) for value in payload.get("servers", []) if self._int(value)],
            imports=imports,
            reviews=reviews,
            data_guard=DataGuardStatusView(
                status=str(guard.get("status") or "Unknown"),
                warnings=self._int(guard.get("warnings")),
                critical=self._int(guard.get("critical")),
                checks=[str(value) for value in guard.get("checks", [])],
            ),
            recent_operations=list(payload.get("recent_operations", [])),
        )

    @staticmethod
    def _int(value: Any) -> int:
        try:
            if value is None:
                return 0
            return int(float(value))
        except (TypeError, ValueError):
            return 0

    def _optional_int(self, value: Any) -> int | None:
        parsed = self._int(value)
        return parsed or None

    @staticmethod
    def _format_ranking_type(value: str) -> str:
        normalized = value.replace("_", " ").strip().title()
        return normalized or "Unknown"
