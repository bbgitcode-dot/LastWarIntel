"""Operational import repository for Sentinel runtime data.

The Command Center reads the latest import run from this repository instead of
benchmark or ground-truth artifacts.  The current implementation persists a
small JSON document; the boundary can later be backed by SQLite/PostgreSQL.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_IMPORT_REPORT = Path("data/latest_import_report.json")


class JsonImportRunRepository:
    def __init__(self, path: Path | str | None = None) -> None:
        self._path = Path(path or DEFAULT_IMPORT_REPORT)

    def load_latest_import(self) -> dict[str, Any] | None:
        if not self._path.exists():
            return None
        try:
            with self._path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    def save_latest_import(self, payload: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

    def describe_source(self) -> str:
        return str(self._path)


def _int(value: Any) -> int:
    try:
        if value is None:
            return 0
        return int(float(value))
    except (TypeError, ValueError):
        return 0



def _safe_float(value: Any) -> float:
    try:
        if value is None or value == "":
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _row_power_recovery_trace(row: dict[str, Any], *, server: Any, ranking_type: str) -> dict[str, Any] | None:
    candidates = row.get("power_recovery_candidates")
    has_recovery = row.get("power_recovered_from") is not None or bool(candidates) or bool(row.get("power_recovery_status"))
    if not has_recovery:
        return None

    candidate_list = candidates if isinstance(candidates, list) else []
    return {
        "server": server if isinstance(server, int) else None,
        "ranking_type": ranking_type,
        "source_file": row.get("source_file") or "",
        "rank": _int(row.get("rank")) or _int(row.get("computed_rank")) or None,
        "ocr_rank": _int(row.get("ocr_rank")) or None,
        "name": row.get("name") or row.get("player_name") or "",
        "power_original": _int(row.get("power_recovered_from")) or _int(row.get("power_original")) or _int(row.get("power")) or None,
        "power_selected": _int(row.get("power")) or None,
        "status": row.get("power_recovery_status") or row.get("power_sanity_status") or "unknown",
        "method": row.get("power_recovery_method") or "",
        "confidence": _safe_float(row.get("power_sanity_confidence")),
        "candidate_count": _int(row.get("power_candidate_count")) or len(candidate_list),
        "best_candidate": _int(row.get("power_candidate_best")) or None,
        "best_score": _safe_float(row.get("power_candidate_best_score") or row.get("power_recovery_selected_score")),
        "second_candidate": _int(row.get("power_candidate_second")) or None,
        "second_score": _safe_float(row.get("power_candidate_second_score")),
        "margin": _safe_float(row.get("power_candidate_margin")),
        "decision_reason": row.get("power_recovery_selected_reason") or "",
        "candidates": candidate_list,
    }

def _status_for_group(rows: list[dict[str, Any]]) -> tuple[str, int, int]:
    if not rows:
        return "Incomplete", 0, 0
    conflicts = sum(1 for row in rows if row.get("data_guard_conflict") or "server_assignment_conflict" in str(row.get("server_warning") or ""))
    warnings = sum(1 for row in rows if row.get("server_warning") or row.get("rank_warning"))
    if conflicts:
        return "Review", conflicts, 85
    if warnings:
        return "Review", warnings, 90
    return "Ready", 0, 100


def build_import_run_report(
    grouped: dict[tuple[Any, str], list[dict[str, Any]]],
    *,
    screenshots: int,
    runtime_seconds: float,
    output_file: str,
) -> dict[str, Any]:
    server_imports: list[dict[str, Any]] = []
    review_items: list[dict[str, Any]] = []
    total_rows = 0
    servers: set[int] = set()
    recovery_attempts = 0
    recovery_success = 0
    recovery_calibrated = 0
    recovery_confidences: list[float] = []
    power_recovery_traces: list[dict[str, Any]] = []
    power_recovery_confidences: list[float] = []
    import_review_count_total = 0

    for (server, ranking_type), rows in sorted(grouped.items(), key=lambda item: str(item[0])):
        rows = list(rows or [])
        total_rows += len(rows)
        if isinstance(server, int):
            servers.add(server)
        status, review_count, confidence = _status_for_group(rows)
        if ranking_type in {"data_guard_quarantine", "ranking_guard_quarantine"}:
            status = "Quarantine"
            review_count = len(rows)
            confidence = 0
        import_review_count_total += review_count
        group_power_traces: list[dict[str, Any]] = []
        for row in rows:
            if row.get("ranking_recovery_status"):
                recovery_attempts += 1
                if row.get("ranking_recovery_status") == "recovered":
                    recovery_success += 1
                if row.get("ranking_recovery_status") == "calibrated_pass":
                    recovery_calibrated += 1
                try:
                    recovery_confidences.append(float(row.get("ranking_recovery_confidence") or 0))
                except (TypeError, ValueError):
                    pass
            trace = _row_power_recovery_trace(row, server=server, ranking_type=ranking_type)
            if trace:
                group_power_traces.append(trace)
                power_recovery_traces.append(trace)
                if trace.get("confidence"):
                    power_recovery_confidences.append(float(trace["confidence"]))
        group_power_recovered = sum(1 for trace in group_power_traces if trace.get("status") == "recovered")
        group_power_ambiguous = sum(1 for trace in group_power_traces if trace.get("status") in {"ambiguous", "candidate_ambiguous"})
        source_files = sorted({str(row.get("source_file")) for row in rows if row.get("source_file")})
        server_imports.append({
            "server": server if isinstance(server, int) else None,
            "ranking_type": ranking_type,
            "rows": len(rows),
            "status": status,
            "confidence": confidence,
            "review_count": review_count,
            "screenshots": len(source_files),
            "source_files": source_files,
            "source": f"{server}_{ranking_type}",
            "power_recovery_count": group_power_recovered,
            "power_candidate_trace_count": len(group_power_traces),
            "power_ambiguous_count": group_power_ambiguous,
        })
        for row in rows:
            warning = str(row.get("server_warning") or "")
            if ranking_type == "data_guard_quarantine":
                review_items.append({
                    "server": _int(row.get("original_server")) or None,
                    "candidate_server": _int(row.get("candidate_server")) or None,
                    "ranking_type": str(row.get("ranking_type") or "unknown"),
                    "rank": _int(row.get("rank")) or _int(row.get("computed_rank")) or None,
                    "title": "Data Guard quarantine",
                    "description": warning or "Data Guard isolated this block instead of guessing a server assignment.",
                    "severity": "warning",
                    "action": "Review quarantined screenshot block",
                    "reason": "data_guard_quarantine",
                    "screenshot": row.get("source_file") or "",
                })
            elif ranking_type == "ranking_guard_quarantine":
                review_items.append({
                    "server": _int(row.get("original_server")) or None,
                    "ranking_type": str(row.get("original_ranking_type") or row.get("ranking_type") or "unknown"),
                    "expected_ranking_type": str(row.get("expected_ranking_type") or "unknown"),
                    "rank": _int(row.get("rank")) or _int(row.get("computed_rank")) or None,
                    "title": "Ranking Guard quarantine",
                    "description": str(row.get("ranking_guard_warning") or "Ranking Guard isolated this row instead of guessing a ranking type."),
                    "severity": "warning",
                    "action": "Review row ranking-type assignment",
                    "reason": "ranking_guard_quarantine",
                    "screenshot": row.get("source_file") or "",
                })
            elif row.get("data_guard_conflict") or "server_assignment_conflict" in warning:
                review_items.append({
                    "server": server if isinstance(server, int) else None,
                    "ranking_type": ranking_type,
                    "rank": _int(row.get("rank")) or _int(row.get("computed_rank")) or None,
                    "title": "Data Guard server assignment conflict",
                    "description": warning or "Server assignment evidence conflicted during import.",
                    "severity": "warning",
                    "action": "Review screenshot server assignment",
                    "reason": "server_assignment_conflict",
                    "screenshot": row.get("source_file") or "",
                })

    effective_review_count = max(import_review_count_total, len(review_items))
    status = "Review" if effective_review_count else "Ready"
    readiness = 100 if not effective_review_count else max(50, int(round(100 - min(effective_review_count * 5, 50))))
    power_recovered = sum(1 for trace in power_recovery_traces if trace.get("status") == "recovered")
    power_ambiguous = sum(1 for trace in power_recovery_traces if trace.get("status") in {"ambiguous", "candidate_ambiguous"})
    return {
        "schema": "sentinel.import_run.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "runtime_seconds": round(float(runtime_seconds), 2),
        "screenshots": int(screenshots),
        "output_file": output_file,
        "servers": sorted(servers),
        "server_count": len(servers),
        "rows": total_rows,
        "status": status,
        "readiness": readiness,
        "review_count": effective_review_count,
        "review_item_count": len(review_items),
        "import_review_count": import_review_count_total,
        "data_guard": {
            "status": "Warning" if effective_review_count else "Healthy",
            "warnings": effective_review_count,
            "critical": 0,
            "checks": ["server_assignment", "data_quality_loop", "ranking_guard", "ranking_recovery", "quarantine"],
        },
        "ranking_recovery": {
            "attempts": recovery_attempts,
            "success": recovery_success,
            "calibrated_pass": recovery_calibrated,
            "rejected": len([item for item in review_items if item.get("reason") == "ranking_guard_quarantine"]),
            "confidence_avg": round(sum(recovery_confidences) / len(recovery_confidences), 4) if recovery_confidences else 0,
        },
        "power_recovery": {
            "candidate_traces": len(power_recovery_traces),
            "recovered": power_recovered,
            "ambiguous": power_ambiguous,
            "confidence_avg": round(sum(power_recovery_confidences) / len(power_recovery_confidences), 4) if power_recovery_confidences else 0,
            "traces": power_recovery_traces,
        },
        "imports": server_imports,
        "reviews": review_items,
        "recent_operations": [
            {
                "time": "latest",
                "title": "Import completed",
                "detail": f"{screenshots} screenshots · {len(servers)} servers · {total_rows} rows · {runtime_seconds:.2f}s",
                "severity": "success" if not effective_review_count else "warning",
            },
            {
                "time": "latest",
                "title": "Sentinel integrity guards completed",
                "detail": f"{effective_review_count} review item(s) detected",
                "severity": "success" if not effective_review_count else "warning",
            },
        ],
    }
