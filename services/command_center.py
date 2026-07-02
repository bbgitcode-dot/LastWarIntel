"""Static Sentinel Command Center rendering.

The Command Center is intentionally report-driven.  It reads the same JSON
artifacts used by the operational handoff and renders static HTML files.  It
must not duplicate OCR, Data Guard, or recovery logic.
"""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_DIR = Path("output")
DEFAULT_IMPORT_REPORT = Path("data/latest_import_report.json")
DEFAULT_GROUND_TRUTH_REPORT = Path("benchmarks/ground_truth_validation_report.json")
DEFAULT_INFERENCE_REPORT = Path("benchmarks/inference_report.json")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _e(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _num(value: Any, default: str = "0") -> str:
    if value in (None, ""):
        return default
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    return str(value)


def _pct(value: Any) -> str:
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return "n/a"


def _badge_class(status: str) -> str:
    normalized = (status or "").lower()
    if normalized in {"ready", "healthy", "success", "ok"}:
        return "ok"
    if normalized in {"review", "warning", "quarantine"}:
        return "warn"
    if normalized in {"critical", "error", "failed"}:
        return "bad"
    return "neutral"


def _artifact_links(import_report: dict[str, Any] | None) -> str:
    output_file = (import_report or {}).get("output_file") or "output/lastwar_export.xlsx"
    links = [
        (output_file, "Excel Export"),
        (str(DEFAULT_IMPORT_REPORT), "Import Report JSON"),
        (str(DEFAULT_GROUND_TRUTH_REPORT), "Ground Truth JSON"),
        (str(DEFAULT_INFERENCE_REPORT), "Inference JSON"),
        ("review_dashboard.html", "Review Dashboard"),
        ("review_evidence_pack.html", "Evidence Pack"),
    ]
    return "".join(f'<a href="{_e(href)}">{_e(label)}</a>' for href, label in links)


def _metric_card(label: str, value: Any, hint: str = "") -> str:
    return f"""
    <section class="card metric">
      <div class="label">{_e(label)}</div>
      <div class="value">{_e(value)}</div>
      <div class="hint">{_e(hint)}</div>
    </section>
    """


def _server_cards(import_report: dict[str, Any]) -> str:
    imports = import_report.get("imports") or []
    rows = []
    for item in imports:
        server = item.get("server") or "REVIEW"
        status = item.get("status") or "Unknown"
        rows.append(f"""
        <section class="card server-card">
          <div class="row between"><h3>Server {_e(server)}</h3><span class="badge {_badge_class(status)}">{_e(status)}</span></div>
          <div class="sub">{_e(item.get('ranking_type'))}</div>
          <div class="mini-grid">
            <div><b>{_num(item.get('rows'))}</b><span>Rows</span></div>
            <div><b>{_num(item.get('screenshots'))}</b><span>Screens</span></div>
            <div><b>{_num(item.get('power_recovery_count'))}</b><span>Recovered</span></div>
            <div><b>{_num(item.get('power_ambiguous_count'))}</b><span>Ambiguous</span></div>
          </div>
        </section>
        """)
    return "".join(rows) or '<p class="muted">No import groups found.</p>'


def _review_rows(import_report: dict[str, Any], limit: int | None = None) -> str:
    reviews = list(import_report.get("reviews") or [])
    if limit is not None:
        reviews = reviews[:limit]
    if not reviews:
        return '<tr><td colspan="10" class="muted">No review items.</td></tr>'
    rendered = []
    for item in reviews:
        rendered.append(f"""
        <tr>
          <td>{_e(item.get('server') or '')}</td>
          <td>{_e(item.get('ranking_type') or '')}</td>
          <td>{_e(item.get('rank') or '')}</td>
          <td>{_e(item.get('title') or '')}</td>
          <td>{_e(item.get('reason') or '')}</td>
          <td>{_e(item.get('review_ocr_status') or '')}</td>
          <td>{_e(item.get('row_reconstruction_status') or '')}</td>
          <td>{_num(item.get('row_reconstruction_score'), '')}</td>
          <td>{_e(item.get('screenshot') or '')}</td>
          <td>{_e(item.get('description') or '')}</td>
        </tr>
        """)
    return "".join(rendered)


def _power_trace_rows(import_report: dict[str, Any], limit: int = 25) -> str:
    traces = list(((import_report.get("power_recovery") or {}).get("traces") or []))[:limit]
    if not traces:
        return '<tr><td colspan="9" class="muted">No power recovery traces.</td></tr>'
    rendered = []
    for trace in traces:
        status = trace.get("status") or ""
        rendered.append(f"""
        <tr>
          <td>{_e(trace.get('server') or '')}</td>
          <td>{_e(trace.get('ranking_type') or '')}</td>
          <td>{_e(trace.get('rank') or '')}</td>
          <td>{_e(trace.get('name') or '')}</td>
          <td>{_e(trace.get('power_original') or '')}</td>
          <td>{_e(trace.get('power_selected') or '')}</td>
          <td><span class="badge {_badge_class(status)}">{_e(status)}</span></td>
          <td>{_num(trace.get('confidence'), '')}</td>
          <td>{_e(trace.get('decision_reason') or '')}</td>
        </tr>
        """)
    return "".join(rendered)


def _ground_truth_panel(ground_truth: dict[str, Any] | None) -> str:
    if not ground_truth:
        return '<p class="muted">No ground-truth validation report found.</p>'
    return "".join([
        _metric_card("Precision", _pct(ground_truth.get("precision")), "matched rows / OCR scope"),
        _metric_card("Recall", _pct(ground_truth.get("recall")), "ground-truth coverage"),
        _metric_card("F1", _num(ground_truth.get("f1")), "validation harmonic mean"),
        _metric_card("Score", _num(ground_truth.get("score")), f"Server {ground_truth.get('validation_server', 'n/a')} {ground_truth.get('validation_ranking_type', '')}"),
    ])


def _base_css() -> str:
    return """
    :root { --bg:#0f172a; --panel:#111c33; --panel2:#17233d; --text:#e5e7eb; --muted:#94a3b8; --ok:#16a34a; --warn:#f59e0b; --bad:#ef4444; --line:#334155; --accent:#38bdf8; }
    * { box-sizing: border-box; }
    body { margin:0; font-family: Segoe UI, Roboto, Arial, sans-serif; background:var(--bg); color:var(--text); }
    header { padding:28px 32px; background:linear-gradient(135deg,#111827,#0f172a 60%,#082f49); border-bottom:1px solid var(--line); }
    h1 { margin:0 0 6px 0; font-size:28px; } h2 { margin:28px 0 14px; } h3 { margin:0; font-size:17px; }
    main { padding:24px 32px 40px; }
    .muted,.hint,.sub { color:var(--muted); } .sub { margin-top:3px; }
    .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:14px; }
    .server-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:14px; }
    .card { background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:16px; box-shadow: 0 10px 24px rgba(0,0,0,.18); }
    .metric .label { color:var(--muted); font-size:13px; } .metric .value { font-size:30px; font-weight:750; margin:8px 0; }
    .row { display:flex; gap:10px; align-items:center; } .between { justify-content:space-between; }
    .badge { display:inline-block; padding:4px 9px; border-radius:999px; font-size:12px; font-weight:700; background:#475569; color:white; }
    .badge.ok { background:rgba(22,163,74,.18); color:#86efac; border:1px solid rgba(22,163,74,.4); }
    .badge.warn { background:rgba(245,158,11,.18); color:#fcd34d; border:1px solid rgba(245,158,11,.45); }
    .badge.bad { background:rgba(239,68,68,.18); color:#fca5a5; border:1px solid rgba(239,68,68,.45); }
    .mini-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin-top:14px; }
    .mini-grid div { background:var(--panel2); border-radius:10px; padding:10px; } .mini-grid b { display:block; font-size:18px; } .mini-grid span { color:var(--muted); font-size:11px; }
    table { width:100%; border-collapse:collapse; background:var(--panel); border:1px solid var(--line); border-radius:14px; overflow:hidden; }
    th,td { padding:10px 12px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; font-size:13px; } th { color:#bfdbfe; background:#172554; position:sticky; top:0; }
    tr:hover td { background:#17233d; } .table-wrap { overflow:auto; max-height:620px; border-radius:14px; }
    .links a { display:inline-block; color:#bae6fd; margin:6px 10px 0 0; text-decoration:none; border:1px solid var(--line); padding:8px 10px; border-radius:10px; background:rgba(56,189,248,.08); }
    .notice { border-left:4px solid var(--accent); padding:12px 14px; background:rgba(56,189,248,.09); border-radius:10px; margin-top:14px; }
    .evidence-card { margin-bottom:16px; } .evidence-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:12px; margin:14px 0; }
    .evidence-grid > div, .decision, .action, .screenshot-ref { background:var(--panel2); border:1px solid var(--line); border-radius:12px; padding:12px; margin-top:10px; }
    .label { color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.06em; } .action { border-left:4px solid var(--warn); } details { margin-top:12px; } summary { cursor:pointer; color:#bae6fd; font-weight:700; } .small { max-height:360px; margin-top:10px; }
    """



def _candidate_rows(trace: dict[str, Any]) -> str:
    candidates = trace.get("candidates") or []
    if not candidates:
        return '<tr><td colspan="4" class="muted">No candidate list recorded.</td></tr>'
    rendered = []
    for idx, candidate in enumerate(candidates[:8], start=1):
        reasons = ", ".join(str(v) for v in candidate.get("reasons") or [])
        rendered.append(f"""
        <tr>
          <td>{idx}</td>
          <td><b>{_e(candidate.get('value') or '')}</b></td>
          <td>{_num(candidate.get('score'), '')}</td>
          <td>{_e(reasons)}</td>
        </tr>
        """)
    return "".join(rendered)


def _trace_key(trace: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(trace.get("source_file") or ""),
        str(trace.get("ranking_type") or ""),
        str(trace.get("rank") or ""),
    )


def _build_trace_index(import_report: dict[str, Any]) -> dict[tuple[str, str, str], dict[str, Any]]:
    traces = (import_report.get("power_recovery") or {}).get("traces") or []
    index: dict[tuple[str, str, str], dict[str, Any]] = {}
    for trace in traces:
        index[_trace_key(trace)] = trace
    return index


def _review_trace_for(review: dict[str, Any], trace_index: dict[tuple[str, str, str], dict[str, Any]]) -> dict[str, Any] | None:
    key = (
        str(review.get("screenshot") or ""),
        str(review.get("ranking_type") or ""),
        str(review.get("rank") or ""),
    )
    return trace_index.get(key)


def _suggested_action(review: dict[str, Any], trace: dict[str, Any] | None) -> str:
    reason = str(review.get("reason") or "")
    description = str(review.get("description") or "")
    if reason == "data_guard_quarantine" or "server_assignment_conflict" in description:
        return "Check the original screenshot header/server marker. Keep quarantined unless server identity is visually confirmed."
    if trace and trace.get("status") == "ambiguous":
        margin = trace.get("margin")
        return f"Compare best and second power candidates. Do not promote automatically; margin={_num(margin, 'n/a')} is below safe cut-off."
    if "alliance_power_outlier" in description:
        return "Validate whether this is a true alliance-power row or an OCR/ranking-type mix-up."
    if review.get("row_reconstruction_status") == "no_promotion":
        return "Inspect row position between trusted neighbouring ranks; candidate was not strong enough for guarded promotion."
    return "Manual visual review recommended before changing Operational Truth."


def _evidence_items(import_report: dict[str, Any]) -> list[dict[str, Any]]:
    reviews = list(import_report.get("reviews") or [])
    trace_index = _build_trace_index(import_report)
    items = []
    for idx, review in enumerate(reviews, start=1):
        trace = _review_trace_for(review, trace_index)
        items.append({
            "id": f"REV-{idx:03d}",
            "server": review.get("server"),
            "candidate_server": review.get("candidate_server"),
            "ranking_type": review.get("ranking_type"),
            "rank": review.get("rank"),
            "title": review.get("title"),
            "reason": review.get("reason"),
            "description": review.get("description"),
            "screenshot": review.get("screenshot"),
            "screenshot_path": f"../screenshots/{review.get('screenshot')}" if review.get("screenshot") else "",
            "review_ocr_status": review.get("review_ocr_status"),
            "row_reconstruction_status": review.get("row_reconstruction_status"),
            "row_reconstruction_score": review.get("row_reconstruction_score"),
            "power_original": trace.get("power_original") if trace else None,
            "power_selected": trace.get("power_selected") if trace else None,
            "best_candidate": trace.get("best_candidate") if trace else None,
            "second_candidate": trace.get("second_candidate") if trace else None,
            "best_score": trace.get("best_score") if trace else None,
            "second_score": trace.get("second_score") if trace else None,
            "margin": trace.get("margin") if trace else None,
            "decision_reason": trace.get("decision_reason") if trace else review.get("description"),
            "suggested_action": _suggested_action(review, trace),
            "trace": trace,
        })
    return items


def _evidence_json(import_report: dict[str, Any] | None) -> dict[str, Any]:
    report = import_report or {}
    return {
        "schema": "sentinel.review_evidence_pack.v1",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_report_created_at": report.get("created_at"),
        "status": report.get("status"),
        "readiness": report.get("readiness"),
        "review_item_count": report.get("review_item_count", 0),
        "items": _evidence_items(report),
    }


def _evidence_cards(import_report: dict[str, Any]) -> str:
    items = _evidence_items(import_report)
    if not items:
        return '<section class="card"><p class="muted">No review evidence items.</p></section>'
    cards = []
    for item in items:
        trace = item.get("trace") or {}
        img = ""
        if item.get("screenshot"):
            img = f'<div class="screenshot-ref"><div class="label">Screenshot</div><a href="{_e(item.get("screenshot_path"))}">{_e(item.get("screenshot"))}</a></div>'
        cards.append(f"""
        <section class="card evidence-card">
          <div class="row between"><h3>{_e(item.get('id'))} · {_e(item.get('title'))}</h3><span class="badge {_badge_class('warning')}">{_e(item.get('reason'))}</span></div>
          <div class="evidence-grid">
            <div><div class="label">Location</div><b>Server {_e(item.get('server') or 'REVIEW')}</b><div class="hint">{_e(item.get('ranking_type'))} · rank {_e(item.get('rank'))}</div></div>
            <div><div class="label">Power</div><b>{_e(item.get('power_original') or 'n/a')}</b><div class="hint">selected {_e(item.get('power_selected') or 'n/a')}</div></div>
            <div><div class="label">Best vs second</div><b>{_e(item.get('best_candidate') or 'n/a')} / {_e(item.get('second_candidate') or 'n/a')}</b><div class="hint">margin {_num(item.get('margin'), 'n/a')}</div></div>
            <div><div class="label">Review status</div><b>{_e(item.get('review_ocr_status') or 'n/a')}</b><div class="hint">row recon {_e(item.get('row_reconstruction_status') or 'n/a')}</div></div>
          </div>
          {img}
          <div class="decision"><b>Decision evidence:</b> {_e(item.get('decision_reason') or '')}</div>
          <div class="action"><b>Suggested action:</b> {_e(item.get('suggested_action') or '')}</div>
          <details><summary>Candidate details</summary><div class="table-wrap small"><table><thead><tr><th>#</th><th>Candidate</th><th>Score</th><th>Reasons</th></tr></thead><tbody>{_candidate_rows(trace)}</tbody></table></div></details>
        </section>
        """)
    return "".join(cards)


def render_review_evidence_pack(import_report: dict[str, Any] | None) -> str:
    report = import_report or {}
    status = report.get("status") or "No report"
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sentinel Review Evidence Pack</title><style>{_base_css()}</style></head>
<body><header><h1>Sentinel Review Evidence Pack</h1><div class="muted">Generated {generated_at} · <span class="badge {_badge_class(status)}">{_e(status)}</span></div>
<div class="links"><a href="command_center.html">Command Center</a><a href="review_dashboard.html">Review Dashboard</a>{_artifact_links(import_report)}</div></header><main>
<section class="grid">
{_metric_card('Review Items', report.get('review_item_count', 0), 'evidence cards')}
{_metric_card('Readiness', report.get('readiness', 'n/a'), 'operational gate')}
{_metric_card('Power Recovered', (report.get('power_recovery') or {}).get('recovered', 0), f"{(report.get('power_recovery') or {}).get('ambiguous', 0)} ambiguous")}
{_metric_card('Data Guard', (report.get('data_guard') or {}).get('status', 'n/a'), f"{(report.get('data_guard') or {}).get('warnings', 0)} warning(s)")}
</section>
<div class="notice">This page is intentionally narrower than the Command Center: it shows only the evidence needed to decide review items. It does not promote rows or alter exports.</div>
<h2>Review Evidence</h2>{_evidence_cards(report)}
</main></body></html>"""

def render_command_center(import_report: dict[str, Any] | None, ground_truth: dict[str, Any] | None, inference: dict[str, Any] | None) -> str:
    report = import_report or {}
    data_guard = report.get("data_guard") or {}
    power = report.get("power_recovery") or {}
    review_ocr = report.get("review_ocr") or {}
    row_recon = report.get("row_reconstruction") or {}
    status = report.get("status") or "No report"
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    inference_rows = len((inference or {}).get("inferences") or (inference or {}).get("rows") or []) if inference else 0
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sentinel Command Center</title><style>{_base_css()}</style></head>
<body><header><h1>Sentinel Command Center</h1><div class="muted">Generated {generated_at} · Report status <span class="badge {_badge_class(status)}">{_e(status)}</span></div>
<div class="links">{_artifact_links(import_report)}</div></header><main>
<section class="grid">
{_metric_card('Readiness', report.get('readiness', 'n/a'), 'Operational confidence gate')}
{_metric_card('Servers', report.get('server_count', 0), ', '.join(str(v) for v in report.get('servers', [])))}
{_metric_card('Screenshots', report.get('screenshots', 0), f"Runtime {_num(report.get('runtime_seconds'))}s")}
{_metric_card('Rows', report.get('rows', 0), 'export/report rows')}
{_metric_card('Review Items', report.get('review_item_count', 0), f"DataGuard {data_guard.get('status', 'n/a')}")}
{_metric_card('Power Recovered', power.get('recovered', 0), f"{power.get('ambiguous', 0)} ambiguous")}
{_metric_card('Review OCR', review_ocr.get('promoted', 0), f"{review_ocr.get('attempted', 0)} attempted")}
{_metric_card('Row Reconstruction', row_recon.get('promoted', 0), f"{row_recon.get('attempted', 0)} attempted")}
</section>
<div class="notice">Data Quality remains the source of truth: this dashboard visualizes reports only. It does not change OCR, recovery, quarantine, or export decisions.</div>
<h2>Server Overview</h2><section class="server-grid">{_server_cards(report)}</section>
<h2>Ground Truth</h2><section class="grid">{_ground_truth_panel(ground_truth)}</section>
<h2>Recent Review Items</h2><div class="table-wrap"><table><thead><tr><th>Server</th><th>Ranking</th><th>Rank</th><th>Title</th><th>Reason</th><th>Review OCR</th><th>Row Recon</th><th>Score</th><th>Screenshot</th><th>Description</th></tr></thead><tbody>{_review_rows(report, limit=30)}</tbody></table></div>
<h2>Power Recovery Traces</h2><div class="table-wrap"><table><thead><tr><th>Server</th><th>Ranking</th><th>Rank</th><th>Name</th><th>Original</th><th>Selected</th><th>Status</th><th>Confidence</th><th>Decision</th></tr></thead><tbody>{_power_trace_rows(report)}</tbody></table></div>
<h2>Inference</h2><section class="card"><b>{_e(inference_rows)}</b> inference rows detected in the latest inference report. Inference remains read-only unless promoted by explicit guarded runtime logic.</section>
</main></body></html>"""


def render_review_dashboard(import_report: dict[str, Any] | None) -> str:
    report = import_report or {}
    status = report.get("status") or "No report"
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sentinel Review Dashboard</title><style>{_base_css()}</style></head>
<body><header><h1>Sentinel Review Dashboard</h1><div class="muted">Generated {generated_at} · <span class="badge {_badge_class(status)}">{_e(status)}</span></div>
<div class="links"><a href="command_center.html">Command Center</a>{_artifact_links(import_report)}</div></header><main>
<section class="grid">
{_metric_card('Review Items', report.get('review_item_count', 0), 'rows requiring attention')}
{_metric_card('Import Review Count', report.get('import_review_count', 0), 'guard warnings')}
{_metric_card('Readiness', report.get('readiness', 'n/a'), 'operational gate')}
</section>
<h2>All Review Items</h2><div class="table-wrap"><table><thead><tr><th>Server</th><th>Ranking</th><th>Rank</th><th>Title</th><th>Reason</th><th>Review OCR</th><th>Row Recon</th><th>Score</th><th>Screenshot</th><th>Description</th></tr></thead><tbody>{_review_rows(report)}</tbody></table></div>
</main></body></html>"""


def generate_command_center(
    *,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    import_report_path: Path | str = DEFAULT_IMPORT_REPORT,
    ground_truth_report_path: Path | str = DEFAULT_GROUND_TRUTH_REPORT,
    inference_report_path: Path | str = DEFAULT_INFERENCE_REPORT,
) -> dict[str, str]:
    """Render static Command Center HTML from latest JSON reports."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    import_report = _load_json(Path(import_report_path))
    ground_truth = _load_json(Path(ground_truth_report_path))
    inference = _load_json(Path(inference_report_path))

    command_center = output_path / "command_center.html"
    review_dashboard = output_path / "review_dashboard.html"
    review_evidence_pack = output_path / "review_evidence_pack.html"
    review_evidence_json = output_path / "review_evidence_pack.json"
    command_center.write_text(render_command_center(import_report, ground_truth, inference), encoding="utf-8")
    review_dashboard.write_text(render_review_dashboard(import_report), encoding="utf-8")
    review_evidence_pack.write_text(render_review_evidence_pack(import_report), encoding="utf-8")
    review_evidence_json.write_text(json.dumps(_evidence_json(import_report), ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "command_center": str(command_center),
        "review_dashboard": str(review_dashboard),
        "review_evidence_pack": str(review_evidence_pack),
        "review_evidence_json": str(review_evidence_json),
    }
