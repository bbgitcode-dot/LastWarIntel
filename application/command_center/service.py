"""Command Center service.

The Command Center consumes application services and domain view models. It does
not read validator files, benchmark artifacts, or parser internals directly.
"""

from __future__ import annotations

from pathlib import Path

from application.data_quality.service import DataQualityService
from application.operational_import.service import OperationalImportService
from version import __version__

from .models import (
    ActivityItem,
    AttentionItem,
    CommandCenterViewModel,
    MissionViewModel,
    OperationalMetric,
    StatusBadge,
    SystemComponent,
)


class CommandCenterService:
    """Build the user-facing Command Center model."""

    def __init__(self, database_path: Path | None = None) -> None:
        self._database_path = database_path or Path("data/lastwarintel.sqlite")
        self._quality_service = DataQualityService()
        self._import_service = OperationalImportService()

    def get_command_center(self) -> CommandCenterViewModel:
        database_exists = self._database_path.exists()
        database_tone = "success" if database_exists else "warning"
        database_detail = "SQLite ready" if database_exists else "SQLite file not found yet"
        latest_import = self._import_service.get_dashboard()
        quality = self._quality_service.get_dashboard()
        summary = quality.summary

        if latest_import.has_import:
            readiness = latest_import.readiness
            if latest_import.review_count > 0:
                status = StatusBadge("Review Required", "warning", f"{latest_import.review_count} Data Guard review items open")
            else:
                status = StatusBadge("Ready", "success", "Latest import operational")

            mission = self._build_import_mission(latest_import.status, latest_import.review_count, latest_import.server_count)
            attention_items = [
                AttentionItem(
                    title=item.title,
                    description=item.description,
                    severity=item.severity,
                    action=item.action,
                )
                for item in latest_import.reviews[:5]
            ]
            if not attention_items:
                attention_items = [
                    AttentionItem(
                        title="No Data Guard review required",
                        description="Latest import has no server assignment conflicts.",
                        severity="success",
                        action="Proceed to analysis",
                    )
                ]

            metrics = [
                OperationalMetric("Operational Readiness", f"{readiness}%", latest_import.status, "success" if readiness >= 90 else "warning"),
                OperationalMetric("Latest Import", f"{latest_import.server_count} servers", f"{latest_import.screenshots} screenshots · {latest_import.runtime_seconds:.2f}s", "success"),
                OperationalMetric("Rows Imported", str(latest_import.rows), latest_import.output_file or "latest export", "info"),
                OperationalMetric("Data Guard", latest_import.data_guard.status, f"{latest_import.data_guard.warnings} warning(s)", "success" if latest_import.data_guard.warnings == 0 else "warning"),
            ]
            activity = [
                ActivityItem(str(op.get("time", "latest")), str(op.get("title", "Operation")), str(op.get("detail", "")), str(op.get("severity", "info")))
                for op in latest_import.recent_operations
            ]

        elif quality.has_report:
            readiness = int(round(summary.f1 * 100)) if summary.f1 else 0
            if summary.bad_matches > 0:
                status = StatusBadge("Review Required", "warning", "Validation found bad matches")
            elif quality.reviews:
                status = StatusBadge("Review Required", "warning", f"{len(quality.reviews)} review items open")
            else:
                status = StatusBadge("Ready", "success", "Validated data online")

            mission = self._build_quality_mission(readiness, len(quality.reviews), summary.unresolved_gap_rows)
            attention_items = [
                AttentionItem(
                    title=item.title,
                    description=item.description,
                    severity=item.severity,
                    action=item.action,
                )
                for item in quality.reviews[:5]
            ]
            if not attention_items:
                attention_items = [
                    AttentionItem(
                        title="No operational review required",
                        description="Latest validation report has no open review items.",
                        severity="success",
                        action="Proceed to analysis",
                    )
                ]

            metrics = [
                OperationalMetric("Operational Readiness", f"{readiness}%", f"F1 {summary.f1:.4f}", "success" if readiness >= 85 else "warning"),
                OperationalMetric("Pending Reviews", str(len(quality.reviews)), f"{summary.unresolved_gap_rows} unresolved rows", "warning" if quality.reviews else "success"),
                OperationalMetric("Valid Matches", f"{summary.matched_rows}/{summary.ground_truth_rows}", f"Precision {summary.precision:.1%}", "success"),
                OperationalMetric("Bad Matches", str(summary.bad_matches), "Blocked instead of guessed", "success" if summary.bad_matches == 0 else "danger"),
            ]
            activity = [
                ActivityItem(str(op["time"]), str(op["title"]), str(op["detail"]), str(op["severity"]))
                for op in quality.recent_operations
            ]
        else:
            readiness = 0
            status = StatusBadge("Healthy", "success", "Service online")
            mission = MissionViewModel(
                title="System ready for operational review",
                description="The service foundation is online. Run a validation report to populate real data.",
                action="Run import validation",
                tone="warning",
                effort="Report pending",
            )
            attention_items = [
                AttentionItem(
                    title="No operational quality report found",
                    description="No operational quality report is available yet.",
                    severity="warning",
                    action="Run import validation",
                )
            ]
            metrics = [
                OperationalMetric("Operational Readiness", "Pending", "No quality report", "warning"),
                OperationalMetric("Pending Reviews", "—", "Report not connected", "neutral"),
                OperationalMetric("Imports Today", "—", "Import center pending", "neutral"),
                OperationalMetric("Database", "OK" if database_exists else "WARN", database_detail, database_tone),
            ]
            activity = [
                ActivityItem("now", "Command Center initialized", "Base layout, navigation and status shell are active.", "success"),
                ActivityItem("next", "Run validation", "Quality metrics will appear after the validator writes its report.", "info"),
            ]

        return CommandCenterViewModel(
            title="Sentinel Command Center",
            subtitle="Observe. Understand. Decide.",
            version=__version__,
            status=status,
            readiness=readiness,
            mission=mission,
            attention_items=attention_items,
            metrics=metrics,
            components=[
                SystemComponent("API", "Online", "FastAPI service responding", "success"),
                SystemComponent("Database", "Ready" if database_exists else "Pending", database_detail, database_tone),
                SystemComponent("Data Guard", latest_import.data_guard.status if latest_import.has_import else "Pending", latest_import.source, "success" if latest_import.has_import and latest_import.data_guard.warnings == 0 else "warning"),
                SystemComponent("Cockpit", "Online", "Command Center active", "success"),
            ],
            activity=activity,
        )

    @staticmethod
    def _build_import_mission(status: str, reviews: int, server_count: int) -> MissionViewModel:
        if reviews > 0:
            return MissionViewModel(
                title=f"Resolve {reviews} Sentinel Data Guard review item{'s' if reviews != 1 else ''}",
                description=f"Latest import processed {server_count} server(s), but Data Guard blocked suspicious assignment evidence.",
                action="Open Imports and review server assignment conflicts",
                tone="warning",
                effort="2–5 min",
            )
        return MissionViewModel(
            title="Latest import ready",
            description=f"Sentinel processed {server_count} server(s) and Data Guard found no assignment conflicts.",
            action="Proceed to Data Quality or strategic analysis",
            tone="success",
            effort="Ready",
        )

    @staticmethod
    def _build_quality_mission(readiness: int, reviews: int, unresolved_rows: int) -> MissionViewModel:
        if reviews > 0:
            return MissionViewModel(
                title=f"Close {reviews} operational review item{'s' if reviews != 1 else ''}",
                description=f"Latest validation is usable, but {unresolved_rows} rows still need targeted screenshot review.",
                action="Open Data Quality and capture the suggested rank blocks",
                tone="warning",
                effort="2–5 min",
            )
        if readiness >= 90:
            return MissionViewModel(
                title="Data ready for intelligence analysis",
                description="The latest validation report has no open review items.",
                action="Proceed to strategic analysis",
                tone="success",
                effort="Ready",
            )
        return MissionViewModel(
            title="Improve operational readiness",
            description="Data is loaded, but confidence is below the preferred operational threshold.",
            action="Review low-confidence rows",
            tone="warning",
            effort="Review required",
        )
