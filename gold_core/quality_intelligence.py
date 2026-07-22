from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
import re
import pandas as pd

PHASE = "v0.9.5.147_gold_core_zero_iii"


def _b(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"1", "true", "yes", "y"}


def _s(v: Any) -> str:
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except Exception:
        pass
    return str(v).strip()


def _n(v: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(v):
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def _slug(value: Any) -> str:
    text = re.sub(r"[^A-Za-z0-9]+", "-", _s(value)).strip("-")
    return text[:48] or "unknown"


def _case_id(row: pd.Series) -> str:
    # Stable across display/OCR changes: server + rank identify a benchmark case.
    return f"S{_s(row.get('server', '?'))}-R{_s(row.get('rank', '?'))}"


def _heuristic_classify(row: pd.Series) -> tuple[str, float, str, str]:
    """Fallback only. Never overrides an established Gold Core truth chain."""
    reason = _s(row.get("gold_core_elimination_reason", ""))
    block = _s(row.get("display_promotion_block_reason", ""))
    pos = _s(row.get("character_position_action", ""))
    unresolved = int(_n(row.get("display_reconstruction_unresolved_targets", 0)))
    observed = int(_n(row.get("display_reconstruction_observed_votes", 0)))
    if "crop" in reason.lower() or "crop" in block.lower() or pos in {"forced_position_acquisition", "position_adaptive_multicrop_retry"}:
        return "crop_geometry", 0.72, "Run adaptive multi-crop acquisition on weak character positions.", "P1"
    if observed > 0 or "observed_votes" in reason:
        return "vote_conflict", 0.74, "Inspect competing OCR votes and require same-snapshot consensus.", "P1"
    if unresolved > 0 or "unresolved" in reason:
        return "character_segmentation", 0.70, "Re-acquire unresolved positions with tighter segmentation.", "P1"
    if "promotion" in reason.lower() or block:
        return "promotion_guard", 0.68, "Review promotion evidence without relaxing the guard.", "P2"
    if "alliance" in reason.lower() or not _b(row.get("core_alliance_match", False)):
        return "alliance_tag_extraction", 0.66, "Validate Basic-Latin alliance-tag crop and bracket segmentation separately.", "P2"
    if "confusion" in reason.lower() or "substitution" in reason.lower():
        return "glyph_confusion", 0.64, "Collect position-level evidence for the proven glyph-confusion family.", "P2"
    if _b(row.get("alignment_context_gap", False)):
        return "context_gap_read_only", 0.90, "Keep read-only until same-snapshot evidence exists.", "P1"
    return "evidence_conflict", 0.50, "Inspect the full evidence bundle and create a dedicated regression case.", "P3"


def _truth_chain(row: pd.Series) -> dict[str, Any]:
    failure_class = _s(row.get("gold_core_failure_class"))
    failure_domain = _s(row.get("gold_core_failure_domain"))
    fix_lane = _s(row.get("gold_core_fix_lane"))
    next_action = _s(row.get("gold_core_next_safe_action"))
    resolution_action = _s(row.get("gold_core_resolution_action"))
    resolution_lane = _s(row.get("gold_core_resolution_lane"))
    resolution_step = _s(row.get("gold_core_resolution_next_step"))
    priority = _s(row.get("gold_blocker_priority")) or "P2"

    evidence_count = sum(bool(x) for x in (failure_class, failure_domain, fix_lane))
    if evidence_count:
        # Existing validator triage is authoritative. Confidence reflects chain completeness.
        confidence = {1: 0.82, 2: 0.91, 3: 0.98}[evidence_count]
        root_cause = failure_domain or failure_class
        recommendation = resolution_step or next_action or "Follow the established Gold Core fix lane."
        return {
            "classification_source": "established_gold_core_triage",
            "failure_class": failure_class,
            "failure_domain": failure_domain,
            "fix_lane": fix_lane,
            "resolution_action": resolution_action,
            "resolution_lane": resolution_lane,
            "root_cause": root_cause,
            "root_cause_confidence": confidence,
            "priority": priority,
            "recommendation": recommendation,
        }

    cause, confidence, recommendation, heuristic_priority = _heuristic_classify(row)
    return {
        "classification_source": "strike_v_fallback_heuristic",
        "failure_class": "",
        "failure_domain": "",
        "fix_lane": "",
        "resolution_action": resolution_action,
        "resolution_lane": resolution_lane,
        "root_cause": cause,
        "root_cause_confidence": confidence,
        "priority": priority or heuristic_priority,
        "recommendation": recommendation,
    }


def _merge_truth_sources(
    detail: pd.DataFrame,
    blocker_report: pd.DataFrame | None,
    resolution_plan: pd.DataFrame | None,
) -> pd.DataFrame:
    base = detail.copy()
    keys = ["server", "rank"]
    for source in (blocker_report, resolution_plan):
        if source is None or source.empty or not all(k in source.columns for k in keys):
            continue
        useful = [c for c in source.columns if c not in keys and c not in base.columns]
        # Also refresh authoritative fields if base has empty placeholders.
        authoritative = [
            "gold_core_failure_class", "gold_core_failure_domain", "gold_core_fix_lane",
            "gold_core_next_safe_action", "gold_core_resolution_action", "gold_core_resolution_lane",
            "gold_core_resolution_next_step", "gold_core_resolution_guardrail", "gold_blocker_priority",
        ]
        cols = keys + [c for c in set(useful + authoritative) if c in source.columns]
        if len(cols) == len(keys):
            continue
        incoming = source[cols].drop_duplicates(keys)
        base = base.merge(incoming, on=keys, how="left", suffixes=("", "__truth"))
        for col in authoritative:
            truth_col = f"{col}__truth"
            if truth_col not in base.columns:
                continue
            if col not in base.columns:
                base[col] = base[truth_col]
            else:
                empty = base[col].isna() | base[col].astype(str).str.strip().eq("")
                base.loc[empty, col] = base.loc[empty, truth_col]
            base.drop(columns=[truth_col], inplace=True)
    return base


def _recommendation_score(row: dict[str, Any], impact: int) -> float:
    priority_weight = {"P1": 1.0, "P2": 0.75, "P3": 0.50}.get(_s(row.get("priority")), 0.50)
    confidence = _n(row.get("root_cause_confidence"), 0.0)
    impact_weight = min(max(impact, 1), 10) / 10.0
    return round((confidence * 0.55 + priority_weight * 0.30 + impact_weight * 0.15) * 100.0, 2)


def build_gold_core_quality_intelligence(
    detail: pd.DataFrame,
    output_dir: Path,
    blocker_report: pd.DataFrame | None = None,
    resolution_plan: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    enriched = _merge_truth_sources(detail, blocker_report, resolution_plan)

    candidates: list[dict[str, Any]] = []
    for _, r in enriched.iterrows():
        before = _b(r.get("gold_core_blocker_before_elimination", r.get("gold_core_blocker", False)))
        after = _b(r.get("gold_core_blocker_after_elimination", r.get("gold_core_blocker", False)))
        if not (before or after or _b(r.get("gold_core_elimination_candidate", False))):
            continue
        truth = _truth_chain(r)
        candidates.append({
            "case_id": _case_id(r),
            "case_key": f"{_case_id(r)}-{_slug(r.get('expected_name'))}",
            "server": r.get("server", ""),
            "rank": r.get("rank", ""),
            "expected_name": r.get("expected_name", ""),
            "ocr_name": r.get("ocr_name", ""),
            "verified_name_display": r.get("verified_name_display", ""),
            "expected_alliance_display": r.get("expected_alliance_display", ""),
            "ocr_alliance_display": r.get("ocr_alliance_display", ""),
            **truth,
            "recommendation_score": 0.0,
            "expected_impact_cases": 1,
            "elimination_action": r.get("gold_core_elimination_action", ""),
            "elimination_reason": r.get("gold_core_elimination_reason", ""),
            "row_integrity_status": r.get("row_integrity_status", ""),
            "blocker_before": before,
            "blocker_after": after,
            "resolved": bool(before and not after),
            "case_status": "RESOLVED" if before and not after else "OPEN",
            "name_proof_status": r.get("name_proof_status", ""),
            "name_reconstruction_coverage": r.get("name_reconstruction_coverage", 0.0),
            "name_reconstructed_value": r.get("name_reconstructed_value", ""),
            "operational_truth_modified": False,
        })

    cause_counts = Counter(_s(x.get("root_cause")) for x in candidates)
    for row in candidates:
        impact = cause_counts[_s(row.get("root_cause"))]
        row["expected_impact_cases"] = impact
        row["recommendation_score"] = _recommendation_score(row, impact)

    details = pd.DataFrame(candidates)
    if details.empty:
        summary = pd.DataFrame([{
            "phase": PHASE, "root_cause": "", "priority": "", "cases": 0,
            "open_cases": 0, "resolved_cases": 0, "avg_confidence": 0.0,
            "avg_recommendation_score": 0.0, "operational_truth_modified": False,
        }])
    else:
        summary = details.groupby(
            ["classification_source", "failure_class", "failure_domain", "fix_lane", "root_cause", "priority"],
            dropna=False,
        ).agg(
            cases=("case_id", "count"),
            open_cases=("blocker_after", "sum"),
            resolved_cases=("resolved", "sum"),
            avg_confidence=("root_cause_confidence", "mean"),
            avg_recommendation_score=("recommendation_score", "mean"),
        ).reset_index()
        summary.insert(0, "phase", PHASE)
        summary["operational_truth_modified"] = False
        summary = summary.sort_values(
            ["priority", "avg_recommendation_score", "cases"], ascending=[True, False, False]
        ).reset_index(drop=True)

    mem_path = output_dir / "gold_core_failure_memory.json"
    old: dict[str, dict[str, Any]] = {}
    if mem_path.exists():
        try:
            old = {x["case_id"]: x for x in json.loads(mem_path.read_text(encoding="utf-8")).get("cases", [])}
        except Exception:
            old = {}
    now = datetime.now(timezone.utc).isoformat()
    memory: list[dict[str, Any]] = []
    for row in candidates:
        prev = old.get(row["case_id"], {})
        resolved_at = prev.get("resolved_at")
        if row["resolved"] and not resolved_at:
            resolved_at = now
        memory.append({
            **prev,
            **row,
            "first_seen": prev.get("first_seen", now),
            "last_seen": now,
            "times_seen": int(prev.get("times_seen", 0)) + 1,
            "resolved_at": resolved_at,
            "solved_version": prev.get("solved_version") or ("0.9.5.147" if row["resolved"] else ""),
            "resolution_method": prev.get("resolution_method") or ("evidence_bound_name_reconstruction" if row.get("elimination_action") == "clear_gold_core_blocker_evidence_reconstructed_name" else ""),
            "reconstruction_coverage": row.get("name_reconstruction_coverage", prev.get("reconstruction_coverage", 0.0)),
            "regression_version": prev.get("regression_version", ""),
            "fix_owner": prev.get("fix_owner", "unassigned"),
            "regression_required": bool(row["resolved"]),
        })
    memory_df = pd.DataFrame(memory)
    mem_path.write_text(json.dumps({
        "phase": PHASE,
        "updated_at": now,
        "operational_truth_modified": False,
        "cases": memory,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary, details, memory_df


def build_gold_core_case_explorer(
    analytics_rows: pd.DataFrame,
    failure_memory: pd.DataFrame,
    output_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, Path]:
    """Create one cross-report index per Gold Core case plus a generated casebook."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    cases = analytics_rows.copy()
    if cases.empty:
        cases = pd.DataFrame(columns=["case_id", "server", "rank", "expected_name"])

    memory_cols = [
        "case_id", "first_seen", "last_seen", "times_seen", "resolved_at", "solved_version",
        "regression_version", "fix_owner", "regression_required",
    ]
    if not failure_memory.empty:
        available = [c for c in memory_cols if c in failure_memory.columns]
        cases = cases.merge(failure_memory[available].drop_duplicates("case_id"), on="case_id", how="left", suffixes=("", "__memory"))

    report_links = {
        "ground_truth_validation": "ground_truth_validation_report.json",
        "gold_core_blockers": "gold_core_blocker_report.json",
        "gold_core_resolution": "gold_core_resolution_plan_report.json",
        "gold_core_elimination": "gold_core_elimination_report.json",
        "character_acquisition": "character_acquisition_report.json",
        "character_position": "character_position_intelligence_report.json",
        "ocr_evidence": "ocr_evidence_report.json",
        "display_reconstruction": "display_reconstruction_report.json",
        "analytics": "gold_core_analytics_report.json",
        "failure_memory": "gold_core_failure_memory.json",
    }
    for key, filename in report_links.items():
        cases[f"report_{key}"] = filename

    if not cases.empty:
        cases = cases.sort_values(["blocker_after", "priority", "recommendation_score", "rank"], ascending=[False, True, False, True]).reset_index(drop=True)
        actions = cases.groupby(["root_cause", "fix_lane", "recommendation"], dropna=False).agg(
            affected_cases=("case_id", "count"),
            open_cases=("blocker_after", "sum"),
            avg_confidence=("root_cause_confidence", "mean"),
            avg_recommendation_score=("recommendation_score", "mean"),
            case_ids=("case_id", lambda x: ", ".join(map(str, x))),
        ).reset_index().sort_values(["avg_recommendation_score", "affected_cases"], ascending=[False, False]).reset_index(drop=True)
    else:
        actions = pd.DataFrame(columns=["root_cause", "fix_lane", "recommendation", "affected_cases"])

    payload = {
        "phase": PHASE,
        "operational_truth_modified": False,
        "cases": cases.to_dict(orient="records"),
        "prioritized_actions": actions.to_dict(orient="records"),
    }
    (output_dir / "gold_core_case_explorer.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )

    casebook_path = output_dir / "GOLD_CORE_CASEBOOK.md"
    lines = [
        "# Gold Core Casebook", "", f"Generated by {PHASE}.", "",
        "> Read-only quality intelligence. Operational Truth is not modified.", "",
        "## Prioritized Actions", "",
    ]
    if actions.empty:
        lines.append("No Gold Core cases were present in this run.")
    else:
        for _, action in actions.iterrows():
            lines.extend([
                f"### {action.get('root_cause') or 'unclassified'}",
                "",
                f"- Fix lane: `{action.get('fix_lane') or 'unassigned'}`",
                f"- Affected cases: {int(_n(action.get('affected_cases')))}",
                f"- Recommendation score: {_n(action.get('avg_recommendation_score')):.2f}",
                f"- Recommendation: {action.get('recommendation')}",
                f"- Cases: {action.get('case_ids')}", "",
            ])
    lines.extend(["## Cases", ""])
    for _, case in cases.iterrows():
        lines.extend([
            f"### {case.get('case_id')} — Rank {case.get('rank')}: {case.get('expected_name')}", "",
            f"- Status: {'OPEN' if _b(case.get('blocker_after')) else 'RESOLVED'}",
            f"- Expected / OCR: `{case.get('expected_name')}` / `{case.get('ocr_name')}`",
            f"- Failure class: `{case.get('failure_class') or 'unclassified'}`",
            f"- Failure domain: `{case.get('failure_domain') or 'unclassified'}`",
            f"- Fix lane: `{case.get('fix_lane') or 'unassigned'}`",
            f"- Root cause: `{case.get('root_cause')}` ({_n(case.get('root_cause_confidence')):.2%})",
            f"- Classification source: `{case.get('classification_source')}`",
            f"- Recommendation score: {_n(case.get('recommendation_score')):.2f}",
            f"- Next action: {case.get('recommendation')}",
            f"- First / last seen: {case.get('first_seen', '')} / {case.get('last_seen', '')}",
            f"- Occurrences: {int(_n(case.get('times_seen')))}",
            "- Linked reports: `gold_core_blocker_report`, `gold_core_resolution_plan_report`, `ocr_evidence_report`, `character_position_intelligence_report`, `gold_core_analytics_report`",
            "",
        ])
    casebook_path.write_text("\n".join(lines), encoding="utf-8")
    return cases, actions, casebook_path
