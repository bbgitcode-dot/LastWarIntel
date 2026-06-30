"""Application service for Data Quality and operational readiness.

The service consumes operational quality reports through a repository boundary.
Ground truth validation remains a developer/benchmark concern; the Command
Center receives domain models and never reads validator files directly.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from services.quality_repository import JsonQualityReportRepository

from .models import ImportRun, QualityDashboard, QualitySummary, ReviewItem, ServerQuality
from .repository import QualityReportRepository


class DataQualityService:
    """Build operational quality models from repository-backed quality data."""

    def __init__(self, repository: QualityReportRepository | None = None) -> None:
        self._repository = repository or JsonQualityReportRepository()

    def get_dashboard(self) -> QualityDashboard:
        report = self._repository.load_latest_report()
        if not report:
            return self._empty_dashboard()

        summary = self._build_summary(report.get("summary", {}))
        details = list(report.get("details", []))
        servers = self._build_servers(summary, details)
        reviews = self._build_reviews(details)
        imports = self._build_imports(summary, details)
        operations = self._build_recent_operations(summary, reviews)

        return QualityDashboard(
            has_report=True,
            report_path=self._repository.describe_source(),
            summary=summary,
            servers=servers,
            reviews=reviews,
            imports=imports,
            recent_operations=operations,
        )

    def _empty_dashboard(self) -> QualityDashboard:
        return QualityDashboard(
            has_report=False,
            report_path=self._repository.describe_source(),
            summary=QualitySummary(),
            servers=[],
            reviews=[
                ReviewItem(
                    server=0,
                    rank=None,
                    title="No operational quality report found",
                    description="Run an import/validation workflow to publish the latest operational quality report.",
                    severity="warning",
                    action="Run validation",
                    reason="report_missing",
                )
            ],
            imports=[],
            recent_operations=[],
        )

    @staticmethod
    def _int(value: Any) -> int:
        try:
            if value is None:
                return 0
            return int(float(value))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _float(value: Any) -> float:
        try:
            if value is None:
                return 0.0
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _build_summary(self, raw: dict[str, Any]) -> QualitySummary:
        return QualitySummary(
            ground_truth_rows=self._int(raw.get("ground_truth_rows")),
            ocr_rows=self._int(raw.get("ocr_rows")),
            matched_rows=self._int(raw.get("matched_rows")),
            missing_rows=self._int(raw.get("missing_rows")),
            bad_matches=self._int(raw.get("bad_matches")),
            gap_blocks=self._int(raw.get("gap_blocks")),
            gap_rows=self._int(raw.get("gap_rows")),
            unresolved_gap_rows=self._int(raw.get("unresolved_gap_rows")),
            blocked_rank_fallbacks=self._int(raw.get("blocked_rank_fallbacks")),
            gap_resolved_rows=self._int(raw.get("gap_resolved_rows")),
            precision=self._float(raw.get("precision")),
            recall=self._float(raw.get("recall")),
            f1=self._float(raw.get("f1")),
            score=self._float(raw.get("score")),
            usable_identity_matches=self._int(raw.get("usable_identity_matches")),
            power_matches=self._int(raw.get("power_matches")),
            alliance_matches=self._int(raw.get("alliance_matches")),
            name_normalized_matches=self._int(raw.get("name_normalized_matches")),
        )

    def _build_servers(self, summary: QualitySummary, details: list[dict[str, Any]]) -> list[ServerQuality]:
        grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for row in details:
            server = self._int(row.get("server"))
            if server:
                grouped[server].append(row)

        servers: list[ServerQuality] = []
        for server, rows in sorted(grouped.items()):
            missing = [self._int(r.get("rank")) for r in rows if r.get("match_method") == "missing" or r.get("gap_status") == "missing_entry"]
            blocked = [self._int(r.get("rank")) for r in rows if r.get("gap_status") == "blocked_rank_fallback"]
            unresolved = sorted(set(missing + blocked))
            valid = sum(1 for r in rows if bool(r.get("valid_match")))
            expected = len(rows) or summary.ground_truth_rows
            readiness = int(round((valid / expected) * 100)) if expected else 0
            if summary.bad_matches > 0:
                status = "Needs Review"
            elif unresolved:
                status = "Action Required"
            else:
                status = "Ready"

            servers.append(
                ServerQuality(
                    server=server,
                    ranking_type="Total Hero Power",
                    expected_rows=expected,
                    ocr_rows=summary.ocr_rows,
                    matched_rows=valid,
                    readiness=readiness,
                    status=status,
                    missing_ranks=[r for r in missing if r],
                    blocked_ranks=[r for r in blocked if r],
                    unresolved_ranks=[r for r in unresolved if r],
                )
            )
        return servers

    def _build_reviews(self, details: list[dict[str, Any]]) -> list[ReviewItem]:
        reviews: list[ReviewItem] = []
        for row in details:
            status = str(row.get("gap_status") or "")
            method = str(row.get("match_method") or "")
            if status not in {"blocked_rank_fallback", "missing_entry"} and method != "missing":
                continue

            server = self._int(row.get("server"))
            rank = self._int(row.get("rank")) or None
            expected_name = str(row.get("expected_name") or "Unknown")
            expected_power = self._int(row.get("expected_power"))
            screenshot = str(row.get("ground_truth_screenshot") or "")
            if status == "missing_entry" or method == "missing":
                title = f"Server {server} THP rank {rank} missing"
                description = f"No reliable OCR entry exists for {expected_name} ({expected_power:,} THP)."
                severity = "danger"
                action = f"Capture around rank {max((rank or 1) - 2, 1)}–{(rank or 0) + 3}"
            else:
                title = f"Server {server} THP rank {rank} blocked"
                description = "Rank fallback was blocked because name and power evidence contradicted the match."
                severity = "warning"
                action = f"Retake rank block {max((rank or 1) - 1, 1)}–{(rank or 0) + 2}"

            reviews.append(
                ReviewItem(
                    server=server,
                    rank=rank,
                    title=title,
                    description=description,
                    severity=severity,
                    action=action,
                    reason=status or method,
                    screenshot=screenshot,
                )
            )
        return sorted(reviews, key=lambda item: (item.server, item.rank or 999999))

    def _build_imports(self, summary: QualitySummary, details: list[dict[str, Any]]) -> list[ImportRun]:
        by_sheet: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in details:
            sheet = str(row.get("ocr_sheet") or "unassigned")
            by_sheet[sheet].append(row)

        imports: list[ImportRun] = []
        for sheet, rows in sorted(by_sheet.items()):
            server = None
            for row in rows:
                parsed_server = self._int(row.get("server"))
                if parsed_server:
                    server = parsed_server
                    break
            valid = sum(1 for r in rows if bool(r.get("valid_match")))
            rows_count = len(rows)
            confidence = int(round((valid / rows_count) * 100)) if rows_count else 0
            status = "Ready" if confidence >= 95 else "Review" if confidence >= 70 else "Incomplete"
            ranking = "Total Hero Power" if "hero_power" in sheet else "Unknown"
            imports.append(
                ImportRun(
                    source=sheet,
                    ranking_type=ranking,
                    server=server,
                    rows=rows_count,
                    status=status,
                    confidence=confidence,
                    detail=f"{valid}/{rows_count} valid rows",
                )
            )
        return imports

    def _build_recent_operations(self, summary: QualitySummary, reviews: list[ReviewItem]) -> list[dict[str, Any]]:
        operations: list[dict[str, Any]] = [
            {
                "time": "latest",
                "title": "Operational validation loaded",
                "detail": f"{summary.matched_rows}/{summary.ground_truth_rows} valid matches · F1 {summary.f1:.4f}",
                "severity": "success" if summary.bad_matches == 0 else "warning",
            },
            {
                "time": "latest",
                "title": "Quality report available",
                "detail": f"{summary.gap_resolved_rows} gap rows resolved · {summary.unresolved_gap_rows} unresolved rows remain",
                "severity": "info",
            },
        ]
        if reviews:
            operations.append(
                {
                    "time": "next",
                    "title": "Review action required",
                    "detail": f"{len(reviews)} review items require targeted screenshots.",
                    "severity": "warning",
                }
            )
        else:
            operations.append(
                {
                    "time": "next",
                    "title": "Data ready",
                    "detail": "No review items remain for the latest validation report.",
                    "severity": "success",
                }
            )
        return operations
