"""Command Center service.

The Command Center consumes application services and domain view models. It does
not read validator files, benchmark artifacts, or parser internals directly.
"""

from __future__ import annotations

import json
import sqlite3
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
    OperationalReadiness,
    OperationalStatusCard,
    ServerHealthItem,
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
        operational_readiness = self._build_operational_readiness(latest_import)

        if latest_import.has_import:
            readiness = operational_readiness.coverage_percent
            open_review_count = len([item for item in self._load_review_history().get("items", []) if isinstance(item, dict) and item.get("status") == "OPEN"])
            human_review_count = open_review_count or len(latest_import.reviews)
            if human_review_count > 0:
                status = StatusBadge("Review Required", "warning", f"{human_review_count} human review item(s) open")
            elif operational_readiness.missing_data_servers > 0:
                status = StatusBadge("Missing Data", "warning", f"{operational_readiness.missing_data_servers} server(s) missing core rankings")
            elif operational_readiness.operational_servers == operational_readiness.total_servers and operational_readiness.total_servers:
                status = StatusBadge("Ready", "success", "Latest import operational")
            else:
                status = StatusBadge("Review Required", "warning", "Operational coverage incomplete")

            mission = self._build_import_mission(latest_import.status, human_review_count, latest_import.server_count)
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
                OperationalMetric("Operational Coverage", f"{readiness}%", f"{operational_readiness.operational_servers}/{operational_readiness.total_servers} servers operational", "success" if readiness >= 90 else "warning"),
                OperationalMetric("Latest Import", f"{latest_import.server_count} servers", f"{latest_import.screenshots} screenshots · {latest_import.runtime_seconds:.2f}s", "success"),
                OperationalMetric("Rows Imported", str(latest_import.rows), latest_import.output_file or "latest export", "info"),
                OperationalMetric("Data Guard", latest_import.data_guard.status, f"{latest_import.data_guard.warnings} raw warning(s)", "success" if latest_import.data_guard.warnings == 0 else "warning"),
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
            operational_readiness=operational_readiness,
            metrics=metrics,
            components=[
                SystemComponent("API", "Online", "FastAPI service responding", "success"),
                SystemComponent("Database", "Ready" if database_exists else "Pending", database_detail, database_tone),
                SystemComponent("Data Guard", latest_import.data_guard.status if latest_import.has_import else "Pending", latest_import.source, "success" if latest_import.has_import and latest_import.data_guard.warnings == 0 else "warning"),
                SystemComponent("Cockpit", "Online", "Command Center active", "success"),
            ],
            activity=activity,
        )


    def _load_review_history(self) -> dict:
        path = Path("data/review_history.json")
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _load_historical_ranking_coverage(self) -> dict[int, set[str]]:
        """Return server -> ranking types from historical SQLite collections.

        Historical coverage is reference data. It can prove that Sentinel knows a
        server/ranking feed exists, but current-run pending reviews still block
        Operational Truth. Benchmark/Ground Truth files are intentionally not
        read here.
        """
        if not self._database_path.exists() or self._database_path.stat().st_size == 0:
            return {}
        try:
            with sqlite3.connect(self._database_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    """
                    SELECT s.server AS server, rt.name AS ranking_type, COUNT(re.id) AS rows
                    FROM snapshots s
                    JOIN collections c ON c.id = s.collection_id
                    JOIN ranking_entries re ON re.snapshot_id = s.id
                    JOIN ranking_types rt ON rt.id = re.ranking_type_id
                    WHERE c.type LIKE 'historical_%'
                    GROUP BY s.server, rt.name
                    HAVING COUNT(re.id) > 0
                    """
                ).fetchall()
        except (OSError, sqlite3.DatabaseError):
            return {}

        coverage: dict[int, set[str]] = {}
        for row in rows:
            try:
                server = int(row["server"])
            except (TypeError, ValueError):
                continue
            ranking_type = str(row["ranking_type"] or "").lower().replace(" ", "_")
            if ranking_type:
                coverage.setdefault(server, set()).add(ranking_type)
        return coverage

    def _build_operational_readiness(self, latest_import) -> OperationalReadiness:
        """Summarize server-level operational readiness for the Command Center.

        Operational means Sentinel has both core ranking feeds for a server and no
        open human review item for that server. Pending Review is intentionally
        counted before Missing Data because human decisions block Operational
        Truth even if the source coverage is otherwise complete.
        """
        required_rankings = {"alliance_power", "total_hero_power"}
        ranking_by_server: dict[int, set[str]] = {}
        failed_servers: set[int] = set()

        historical_ranking_by_server = self._load_historical_ranking_coverage()
        for server, rankings in historical_ranking_by_server.items():
            ranking_by_server.setdefault(server, set()).update(rankings)

        for item in getattr(latest_import, "imports", []) or []:
            server = getattr(item, "server", None)
            if not server:
                continue
            normalized_ranking = str(getattr(item, "ranking_type", "") or "").lower().replace(" ", "_")
            ranking_by_server.setdefault(int(server), set()).add(normalized_ranking)
            if str(getattr(item, "status", "") or "").lower() in {"failed", "error", "critical"}:
                failed_servers.add(int(server))

        discovered_servers = set(int(server) for server in getattr(latest_import, "servers", []) or [] if int(server or 0))
        discovered_servers.update(ranking_by_server)

        review_history = self._load_review_history()
        pending_servers: set[int] = set()
        for item in review_history.get("items") or []:
            if not isinstance(item, dict) or item.get("status") != "OPEN":
                continue
            try:
                server = int(item.get("server") or 0)
            except (TypeError, ValueError):
                server = 0
            if server:
                pending_servers.add(server)
                discovered_servers.add(server)

        missing_servers = {
            server for server in discovered_servers
            if not required_rankings.issubset(ranking_by_server.get(server, set()))
        }
        operational_servers = {
            server for server in discovered_servers
            if server not in pending_servers
            and server not in missing_servers
            and server not in failed_servers
        }

        total = len(discovered_servers)
        operational_count = len(operational_servers)
        pending_count = len(pending_servers)
        missing_count = len(missing_servers - pending_servers)
        failed_count = len(failed_servers)
        coverage = int(round((operational_count / total) * 100)) if total else 0

        def status_for(server: int) -> tuple[str, str, str]:
            rankings = ranking_by_server.get(server, set())
            missing = sorted(required_rankings - rankings)
            if server in failed_servers:
                return "Import Failed", "danger", "Import produced a failed/error state"
            if server in pending_servers:
                return "Pending Review", "warning", "Human review blocks Operational Truth"
            if missing:
                return "Missing Data", "danger", "Missing " + ", ".join(missing)
            return "Operational", "success", "Core rankings complete and no open review"

        server_health = []
        for server in sorted(discovered_servers):
            status, tone, detail = status_for(server)
            server_health.append(ServerHealthItem(server=server, status=status, tone=tone, href=f"/servers/{server}", detail=detail))

        cards = [
            OperationalStatusCard(
                title="Servers discovered",
                value=str(total),
                subtitle="known from historical dataset, latest import, or reviews",
                tone="info",
                href="/servers",
                description="Open the monitored server landscape.",
            ),
            OperationalStatusCard(
                title="Operational",
                value=str(operational_count),
                subtitle=f"{coverage}% coverage",
                tone="success" if operational_count else "warning",
                href="/servers?status=operational",
                description="Servers with complete core rankings and no open reviews.",
            ),
            OperationalStatusCard(
                title="Pending Review",
                value=str(pending_count),
                subtitle="human decision required",
                tone="warning" if pending_count else "success",
                href="/reviews?status=open",
                description="Open review queue filtered to unresolved items.",
            ),
            OperationalStatusCard(
                title="Missing Data",
                value=str(missing_count),
                subtitle="missing core ranking feed",
                tone="danger" if missing_count else "success",
                href="/quality?filter=missing-data",
                description="Inspect missing or incomplete server evidence.",
            ),
            OperationalStatusCard(
                title="Failed Imports",
                value=str(failed_count),
                subtitle="import error state",
                tone="danger" if failed_count else "success",
                href="/imports?status=failed",
                description="Open import history and failed source groups.",
            ),
        ]

        return OperationalReadiness(
            total_servers=total,
            operational_servers=operational_count,
            pending_review_servers=pending_count,
            missing_data_servers=missing_count,
            failed_import_servers=failed_count,
            coverage_percent=coverage,
            cards=cards,
            server_health=server_health,
        )

    @staticmethod
    def _build_import_mission(status: str, reviews: int, server_count: int) -> MissionViewModel:
        if reviews > 0:
            return MissionViewModel(
                title=f"Resolve {reviews} Sentinel Data Guard review item{'s' if reviews != 1 else ''}",
                description=f"Latest import processed {server_count} server(s), but Data Guard blocked suspicious assignment evidence.",
                action="Open Imports and review server assignment conflicts",
                tone="warning",
                effort="Estimated review effort: 2–5 min",
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
                effort="Estimated review effort: 2–5 min",
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
