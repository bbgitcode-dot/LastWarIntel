"""Static Sentinel Command Center rendering.

The Command Center is intentionally report-driven.  It reads the same JSON
artifacts used by the operational handoff and renders static HTML files.  It
must not duplicate OCR, Data Guard, or recovery logic.
"""

from __future__ import annotations

import hashlib
import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_DIR = Path("output")
DEFAULT_IMPORT_REPORT = Path("data/latest_import_report.json")
DEFAULT_GROUND_TRUTH_REPORT = Path("benchmarks/ground_truth_validation_report.json")
DEFAULT_INFERENCE_REPORT = Path("benchmarks/inference_report.json")
DEFAULT_REVIEW_HISTORY = Path("data/review_history.json")


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
        ("review_center.html", "Review Center"),
        ("review_dashboard.html", "Review Queue"),
        ("review_evidence_pack.html", "Review Detail / Evidence"),
        ("review_history.json", "Review History"),
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
        return '<tr><td colspan="11" class="muted">No review items.</td></tr>'
    rendered = []
    for idx, item in enumerate(reviews, start=1):
        review_id = f"REV-{idx:03d}"
        evidence_link = f'<a href="review_evidence_pack.html#{review_id}">{review_id}</a>'
        rendered.append(f"""
        <tr>
          <td>{evidence_link}</td>
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
    .trace-list { list-style:none; padding:0; margin:10px 0 0; } .trace-list li { padding:9px 10px; border-left:3px solid var(--accent); background:var(--panel2); margin:8px 0; border-radius:8px; }
    .tabs { display:flex; flex-wrap:wrap; gap:8px; margin:16px 0; } .tabs a { color:#bae6fd; text-decoration:none; border:1px solid var(--line); border-radius:999px; padding:8px 12px; background:rgba(56,189,248,.08); }
    .status-open { color:#fcd34d; font-weight:700; } .status-resolved { color:#86efac; font-weight:700; }
    .evidence-grid > div, .decision, .action, .screenshot-ref { background:var(--panel2); border:1px solid var(--line); border-radius:12px; padding:12px; margin-top:10px; }
    .label { color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.06em; } .action { border-left:4px solid var(--warn); } details { margin-top:12px; } summary { cursor:pointer; color:#bae6fd; font-weight:700; } .small { max-height:360px; margin-top:10px; }
    """



def _candidate_rows(trace: dict[str, Any]) -> str:
    candidates = trace.get("candidates") or []
    if not candidates:
        return '<tr><td colspan="5" class="muted">No candidate list recorded.</td></tr>'
    rendered = []
    for idx, candidate in enumerate(candidates[:8], start=1):
        reasons = ", ".join(str(v) for v in candidate.get("reasons") or [])
        rendered.append(f"""
        <tr>
          <td>{idx}</td>
          <td><b>{_e(candidate.get('value') or '')}</b></td>
          <td>{_num(candidate.get('score'), '')}</td>
          <td>{_num(candidate.get('digit_preservation_score'), '')}</td>
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


def _build_trace_index(import_report: dict[str, Any]) -> dict[str, Any]:
    """Build exact and screenshot-local indexes for power recovery traces.

    Review rows may describe the user-facing expected ranking type while the
    underlying trace was produced in the synthetic ranking_guard_quarantine
    group.  Exact matching alone therefore drops the most useful evidence.
    """
    traces = (import_report.get("power_recovery") or {}).get("traces") or []
    exact: dict[tuple[str, str, str], dict[str, Any]] = {}
    by_screenshot: dict[str, list[dict[str, Any]]] = {}
    for trace in traces:
        exact[_trace_key(trace)] = trace
        by_screenshot.setdefault(str(trace.get("source_file") or ""), []).append(trace)
    return {"exact": exact, "by_screenshot": by_screenshot}


def _extract_numeric_hint(text: str, prefix: str) -> float | None:
    marker = f"{prefix}="
    if marker not in text:
        return None
    tail = text.split(marker, 1)[1]
    value = []
    for char in tail:
        if char.isdigit() or char == ".":
            value.append(char)
        else:
            break
    try:
        return float("".join(value)) if value else None
    except ValueError:
        return None


def _trace_match_score(review: dict[str, Any], trace: dict[str, Any]) -> float:
    score = 0.0
    if str(review.get("screenshot") or "") == str(trace.get("source_file") or ""):
        score += 4.0
    if str(review.get("rank") or "") == str(trace.get("rank") or ""):
        score += 2.0
    review_type = str(review.get("ranking_type") or "")
    expected_type = str(review.get("expected_ranking_type") or "")
    trace_type = str(trace.get("ranking_type") or "")
    if trace_type in {review_type, expected_type}:
        score += 2.0
    elif trace_type == "ranking_guard_quarantine" and review.get("reason") == "ranking_guard_quarantine":
        score += 1.0

    description = str(review.get("description") or "")
    best_hint = _extract_numeric_hint(description, "best")
    margin_hint = _extract_numeric_hint(description, "margin")
    if best_hint is not None and trace.get("best_score") is not None:
        if abs(float(trace.get("best_score")) - best_hint) < 0.01:
            score += 2.0
    if margin_hint is not None and trace.get("margin") is not None:
        if abs(float(trace.get("margin")) - margin_hint) < 0.01:
            score += 2.0
    return score


def _review_trace_for(review: dict[str, Any], trace_index: dict[str, Any]) -> dict[str, Any] | None:
    exact = trace_index.get("exact") or {}
    key = (
        str(review.get("screenshot") or ""),
        str(review.get("ranking_type") or ""),
        str(review.get("rank") or ""),
    )
    if key in exact:
        return exact[key]

    expected_key = (
        str(review.get("screenshot") or ""),
        str(review.get("expected_ranking_type") or ""),
        str(review.get("rank") or ""),
    )
    if expected_key in exact:
        return exact[expected_key]

    quarantine_key = (
        str(review.get("screenshot") or ""),
        "ranking_guard_quarantine",
        str(review.get("rank") or ""),
    )
    if quarantine_key in exact:
        return exact[quarantine_key]

    candidates = list((trace_index.get("by_screenshot") or {}).get(str(review.get("screenshot") or ""), []))
    if not candidates:
        return None
    ranked = sorted(((_trace_match_score(review, trace), trace) for trace in candidates), key=lambda item: item[0], reverse=True)
    if ranked and ranked[0][0] >= 4.0:
        return ranked[0][1]
    if len(candidates) == 1:
        return candidates[0]
    return None



def _fmt_power(value: Any) -> str:
    if value in (None, ""):
        return "n/a"
    try:
        return f"{int(value):,}".replace(",", ".")
    except (TypeError, ValueError):
        return str(value)


def _problem_type(review: dict[str, Any], trace: dict[str, Any] | None) -> str:
    reason = str(review.get("reason") or "")
    description = str(review.get("description") or "")
    title = str(review.get("title") or "")
    if reason == "data_guard_quarantine" or "server_assignment_conflict" in description:
        return "server_assignment_unclear"
    if "alliance_power_outlier" in description:
        return "alliance_power_outlier"
    if trace and trace.get("status") == "ambiguous":
        if str(review.get("ranking_type") or "") == "alliance_power":
            return "alliance_power_ambiguous"
        return "power_ambiguous"
    if "rank" in description.lower() or "Ranking Guard" in title:
        return "rank_or_row_unclear"
    if "name" in description.lower():
        return "name_unclear"
    return "manual_review_required"


def _problem_label(problem_type: str) -> str:
    labels = {
        "server_assignment_unclear": "Server-Zuordnung unklar",
        "alliance_power_outlier": "Allianzstärke-Ausreißer",
        "alliance_power_ambiguous": "Allianzstärke nicht eindeutig",
        "power_ambiguous": "Power-Wert nicht eindeutig",
        "rank_or_row_unclear": "Rang oder Zeile nicht eindeutig",
        "name_unclear": "Name nicht eindeutig",
        "manual_review_required": "Manuelle Prüfung nötig",
    }
    return labels.get(problem_type, "Manuelle Prüfung nötig")


def _choice_list(trace: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not trace:
        return [{"label": "Manuelle Eingabe", "value": None, "score": None, "kind": "manual_input"}]
    choices: list[dict[str, Any]] = []
    candidates = list(trace.get("candidates") or [])
    for idx, candidate in enumerate(candidates[:3], start=1):
        choices.append({
            "label": f"Vorschlag {idx}",
            "value": candidate.get("value"),
            "score": candidate.get("score"),
            "digit_preservation_score": candidate.get("digit_preservation_score"),
            "reasons": candidate.get("reasons") or [],
            "kind": "candidate",
        })
    choices.append({"label": "Manuelle Eingabe", "value": None, "score": None, "kind": "manual_input"})
    return choices


def _human_problem_statement(review_id: str, review: dict[str, Any], trace: dict[str, Any] | None) -> str:
    problem_type = _problem_type(review, trace)
    ranking_type = str(review.get("ranking_type") or "Ranking")
    rank = review.get("rank") or "?"
    server = review.get("server") or review.get("candidate_server") or "unbekannt"
    subject = "Datensatz"
    if ranking_type == "alliance_power":
        subject = "Allianzstärke der Allianz"
    elif ranking_type == "total_hero_power":
        subject = "Spieler-Power des Eintrags"

    if problem_type in {"alliance_power_ambiguous", "power_ambiguous"} and trace:
        choices = _choice_list(trace)
        candidate_bits = []
        for choice in choices[:2]:
            if choice.get("value") is not None:
                candidate_bits.append(f"{choice['label']}: {_fmt_power(choice.get('value'))}")
        candidates = ", ".join(candidate_bits) if candidate_bits else "keine sichere Kandidatenliste"
        return f"{review_id}: Ich konnte die {subject} auf Server {server}, Rang {rank}, nicht eindeutig bestimmen. {candidates} oder manuelle Eingabe."

    if problem_type == "alliance_power_outlier":
        return f"{review_id}: Die Allianzstärke auf Server {server}, Rang {rank}, wirkt im lokalen Kontext wie ein Ausreißer. Bitte visuell prüfen, ob Wert und Ranking-Typ wirklich stimmen."

    if problem_type == "server_assignment_unclear":
        return f"{review_id}: Ich konnte den Screenshot-Block nicht eindeutig einem Server zuordnen. Bitte Serverkopf prüfen und den Datensatz nur übernehmen, wenn Server {server} visuell bestätigt ist."

    if problem_type == "name_unclear":
        return f"{review_id}: Der Name des Eintrags auf Server {server}, Rang {rank}, ist nicht eindeutig lesbar. Bitte Name manuell prüfen oder ergänzen."

    if problem_type == "rank_or_row_unclear":
        return f"{review_id}: Rang oder Zeilenposition auf Server {server}, Rang {rank}, ist nicht eindeutig. Bitte Nachbarzeilen prüfen."

    return f"{review_id}: Dieser Datensatz auf Server {server}, Rang {rank}, braucht eine manuelle Prüfung, bevor er Operational Truth werden darf."


def _confidence_label(trace: dict[str, Any] | None) -> str:
    if not trace:
        return "Keine Candidate-Evidenz"
    margin = trace.get("margin")
    try:
        margin_value = float(margin)
    except (TypeError, ValueError):
        return "Candidate-Evidenz vorhanden"
    if margin_value >= 0.12:
        return "stark"
    if margin_value >= 0.06:
        return "mittel"
    return "zu knapp für Auto-Promotion"


def _history_identity(item: dict[str, Any]) -> str:
    """Return the stable business identity of a review item.

    A review can appear in many import runs.  Runtime timestamps must not be
    part of the identity, otherwise every rerun creates a new open review for
    the same unresolved problem.  The identity intentionally follows the human
    review surface: server, ranking type, rank, screenshot, problem type and
    reason.
    """
    return "|".join(str(v or "") for v in [
        item.get("server"),
        item.get("ranking_type"),
        item.get("rank"),
        item.get("screenshot"),
        item.get("problem_type"),
        item.get("reason"),
    ])


def _history_key(item: dict[str, Any]) -> str:
    return hashlib.sha1(_history_identity(item).encode("utf-8")).hexdigest()[:16]


def _history_record_from_evidence(item: dict[str, Any], *, created_at: Any, source_created_at: Any) -> dict[str, Any]:
    key = _history_key(item)
    return {
        "history_key": key,
        "review_identity": _history_identity(item),
        "status": "OPEN",
        "created_at": created_at,
        "last_seen_at": created_at,
        "seen_count": 1,
        "source_report_created_at": source_created_at,
        "review_id": item.get("id"),
        "server": item.get("server"),
        "ranking_type": item.get("ranking_type"),
        "rank": item.get("rank"),
        "reason": item.get("reason"),
        "problem_type": item.get("problem_type"),
        "problem_statement": item.get("problem_statement"),
        "screenshot": item.get("screenshot"),
        "power_original": item.get("power_original"),
        "best_candidate": item.get("best_candidate"),
        "second_candidate": item.get("second_candidate"),
        "margin": item.get("margin"),
        "why_bullets": item.get("why_bullets") or [],
        "explainability_steps": item.get("explainability_steps") or [],
        "choices": item.get("choices") or [],
        "resolution": item.get("resolution_template") or _resolution_template(),
    }


def _merge_history_record(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    """Merge a rerun into an existing review without losing resolution state."""
    status = existing.get("status") or incoming.get("status") or "OPEN"
    resolution = existing.get("resolution") or incoming.get("resolution") or _resolution_template()
    created_at = existing.get("created_at") or incoming.get("created_at")
    seen_count = int(existing.get("seen_count") or 1) + 1

    merged = dict(existing)
    for key, value in incoming.items():
        if key in {"history_key", "review_identity", "status", "created_at", "resolution", "seen_count"}:
            continue
        if value not in (None, "", [], {}):
            merged[key] = value
    merged["history_key"] = incoming.get("history_key") or existing.get("history_key")
    merged["review_identity"] = incoming.get("review_identity") or existing.get("review_identity")
    merged["status"] = status
    merged["created_at"] = created_at
    merged["last_seen_at"] = incoming.get("last_seen_at") or existing.get("last_seen_at")
    merged["seen_count"] = seen_count
    merged["resolution"] = resolution
    return merged


def _history_payload(existing: dict[str, Any] | None, evidence: dict[str, Any]) -> dict[str, Any]:
    payload = existing if isinstance(existing, dict) else {}
    by_identity: dict[str, dict[str, Any]] = {}
    ordered: list[dict[str, Any]] = []

    # First normalize and de-duplicate existing history.  This repairs v0.9.5.59
    # histories where runtime timestamps accidentally created duplicate OPEN
    # items for the same problem.
    for old in list(payload.get("items") or []):
        identity = old.get("review_identity") or _history_identity(old)
        normalized = dict(old)
        normalized["review_identity"] = identity
        normalized["history_key"] = _history_key(normalized)
        normalized.setdefault("last_seen_at", normalized.get("created_at"))
        normalized.setdefault("seen_count", 1)
        normalized["resolution"] = normalized.get("resolution") or _resolution_template()
        if identity in by_identity:
            by_identity[identity] = _merge_history_record(by_identity[identity], normalized)
        else:
            by_identity[identity] = normalized
            ordered.append(normalized)

    source_created_at = evidence.get("source_report_created_at")
    for item in evidence.get("items") or []:
        incoming = _history_record_from_evidence(
            item,
            created_at=evidence.get("created_at"),
            source_created_at=source_created_at,
        )
        identity = incoming["review_identity"]
        if identity in by_identity:
            by_identity[identity] = _merge_history_record(by_identity[identity], incoming)
        else:
            by_identity[identity] = incoming
            ordered.append(incoming)

    # Preserve stable display order while using the merged record for each identity.
    items = [by_identity[item["review_identity"]] for item in ordered if item.get("review_identity") in by_identity]
    items = items[-500:]
    return {
        "schema": "sentinel.review_history.v1",
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "open_count": sum(1 for item in items if item.get("status") == "OPEN"),
        "resolved_count": sum(1 for item in items if item.get("status") == "RESOLVED"),
        "items": items,
    }


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


def _why_bullets(review: dict[str, Any], trace: dict[str, Any] | None, problem_type: str) -> list[str]:
    description = str(review.get("description") or "")
    bullets: list[str] = []
    if trace and trace.get("power_original") is not None:
        bullets.append(f"OCR/Parser lieferte den Ausgangswert {_fmt_power(trace.get('power_original'))}.")
    if trace and trace.get("best_candidate") is not None and trace.get("second_candidate") is not None:
        bullets.append(f"Die besten Kandidaten liegen nah beieinander: {_fmt_power(trace.get('best_candidate'))} vs. {_fmt_power(trace.get('second_candidate'))}.")
    if trace and trace.get("margin") is not None:
        bullets.append(f"Der Score-Abstand beträgt nur {_num(trace.get('margin'), 'n/a')} und liegt unter der sicheren Auto-Promotion-Schwelle.")
    if trace and trace.get("candidates"):
        first = (trace.get("candidates") or [{}])[0]
        reasons = ", ".join(str(v) for v in first.get("reasons") or [])
        if reasons:
            bullets.append(f"Der führende Kandidat wurde durch folgende Evidenz gestützt: {reasons}.")
    if problem_type == "alliance_power_outlier":
        bullets.append("Der Wert weicht stark vom lokalen Allianz-Power-Kontext ab.")
        bullets.append("Es gibt keine ausreichend starke Candidate-Evidenz; visuelle Prüfung ist nötig.")
    if problem_type == "server_assignment_unclear":
        bullets.append("Der Screenshot-Block kollidiert mit der erwarteten Server-Zuordnung.")
    if "power_recovery_candidates_ambiguous" in description and not any("Kandidaten" in b for b in bullets):
        bullets.append("Mehrere plausible Power-Kandidaten wurden gefunden, aber keiner ist eindeutig dominant.")
    if not bullets:
        bullets.append("Sentinel konnte diesen Datensatz nicht ohne menschliche Prüfung in Operational Truth übernehmen.")
    return bullets


def _explainability_steps(review: dict[str, Any], trace: dict[str, Any] | None) -> list[dict[str, Any]]:
    steps = [
        {"stage": "OCR", "status": "captured", "detail": f"Screenshot {review.get('screenshot') or 'n/a'} wurde gelesen."},
        {"stage": "Normalization", "status": "applied", "detail": "Text, Ranking-Typ und Power-Felder wurden normalisiert."},
    ]
    if trace:
        steps.append({"stage": "Power Recovery", "status": str(trace.get("status") or "evaluated"), "detail": f"{trace.get('candidate_count') or 0} Kandidat(en), bester Score {_num(trace.get('best_score'), 'n/a')}, Margin {_num(trace.get('margin'), 'n/a')}."})
    else:
        steps.append({"stage": "Power Recovery", "status": "not_available", "detail": "Keine Candidate-Spur für diesen Review vorhanden."})
    steps.extend([
        {"stage": "Ranking Guard", "status": "quarantine", "detail": str(review.get("description") or review.get("reason") or "Review erforderlich")},
        {"stage": "Data Guard", "status": "protected", "detail": "Operational Truth wurde nicht verändert."},
        {"stage": "Human Review", "status": "open", "detail": "Menschliche Entscheidung erforderlich."},
    ])
    return steps


def _resolution_template() -> dict[str, Any]:
    return {
        "status": "OPEN",
        "selected_choice": None,
        "manual_value": None,
        "manual_name": None,
        "manual_alliance": None,
        "comment": None,
        "reviewer": None,
        "resolved_at": None,
        "resolution_source": "human_review",
    }


def _evidence_items(import_report: dict[str, Any]) -> list[dict[str, Any]]:
    reviews = list(import_report.get("reviews") or [])
    trace_index = _build_trace_index(import_report)
    items = []
    for idx, review in enumerate(reviews, start=1):
        trace = _review_trace_for(review, trace_index)
        review_id = f"REV-{idx:03d}"
        problem_type = _problem_type(review, trace)
        choices = _choice_list(trace)
        why_bullets = _why_bullets(review, trace, problem_type)
        explainability_steps = _explainability_steps(review, trace)
        items.append({
            "id": review_id,
            "problem_type": problem_type,
            "problem_label": _problem_label(problem_type),
            "problem_statement": _human_problem_statement(review_id, review, trace),
            "confidence_label": _confidence_label(trace),
            "choices": choices,
            "why_bullets": why_bullets,
            "explainability_steps": explainability_steps,
            "resolution_template": _resolution_template(),
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
            "trace_status": trace.get("status") if trace else None,
            "trace_source_file": trace.get("source_file") if trace else None,
            "candidate_count": trace.get("candidate_count") if trace else None,
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



def _choice_rows(item: dict[str, Any]) -> str:
    choices = item.get("choices") or []
    if not choices:
        return '<tr><td colspan="4" class="muted">No review choices recorded.</td></tr>'
    rendered = []
    for choice in choices:
        value = _fmt_power(choice.get("value")) if choice.get("value") is not None else "Manuelle Eingabe"
        reasons = ", ".join(str(v) for v in choice.get("reasons") or [])
        rendered.append(f"""
        <tr>
          <td>{_e(choice.get('label') or '')}</td>
          <td><b>{_e(value)}</b></td>
          <td>{_num(choice.get('score'), 'n/a')}</td>
          <td>{_e(reasons)}</td>
        </tr>
        """)
    return "".join(rendered)

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
        <section class="card evidence-card" id="{_e(item.get('id'))}">
          <div class="row between"><h3>{_e(item.get('id'))} · {_e(item.get('problem_label') or item.get('title'))}</h3><span class="badge {_badge_class('warning')}">{_e(item.get('reason'))}</span></div>
          <div class="action"><b>Problem:</b> {_e(item.get('problem_statement') or '')}</div>
          <div class="evidence-grid">
            <div><div class="label">Location</div><b>Server {_e(item.get('server') or 'REVIEW')}</b><div class="hint">{_e(item.get('ranking_type'))} · rank {_e(item.get('rank'))}</div></div>
            <div><div class="label">OCR / Original</div><b>{_e(_fmt_power(item.get('power_original')))}</b><div class="hint">selected {_e(_fmt_power(item.get('power_selected')))}</div></div>
            <div><div class="label">Best vs second</div><b>{_e(_fmt_power(item.get('best_candidate')))} / {_e(_fmt_power(item.get('second_candidate')))}</b><div class="hint">margin {_num(item.get('margin'), 'n/a')} · {_e(item.get('confidence_label') or '')}</div></div>
            <div><div class="label">Review status</div><b>{_e(item.get('review_ocr_status') or 'n/a')}</b><div class="hint">row recon {_e(item.get('row_reconstruction_status') or 'n/a')}</div></div>
            <div><div class="label">Trace</div><b>{_e(item.get('trace_status') or 'not bound')}</b><div class="hint">{_e(item.get('trace_source_file') or 'no trace source')} · candidates {_e(item.get('candidate_count') or 'n/a')}</div></div>
          </div>
          {img}
          <div class="decision"><b>Needed decision:</b> Wähle einen Vorschlag, gib einen Wert manuell ein, oder lasse den Datensatz in Review.</div>
          <details open><summary>Warum?</summary>{_bullet_list(item.get('why_bullets') or [])}</details>
          <details open><summary>Review choices</summary><div class="table-wrap small"><table><thead><tr><th>Option</th><th>Value</th><th>Score</th><th>Reason</th></tr></thead><tbody>{_choice_rows(item)}</tbody></table></div></details>
          <details><summary>Explainability trace</summary>{_trace_steps(item.get('explainability_steps') or [])}</details>
          <div class="decision"><b>Decision evidence:</b> {_e(item.get('decision_reason') or '')}</div>
          <div class="action"><b>Suggested action:</b> {_e(item.get('suggested_action') or '')}</div>
          <details><summary>Candidate details</summary><div class="table-wrap small"><table><thead><tr><th>#</th><th>Candidate</th><th>Score</th><th>Digit</th><th>Reasons</th></tr></thead><tbody>{_candidate_rows(trace)}</tbody></table></div></details>
        </section>
        """)
    return "".join(cards)


def _bullet_list(values: list[Any]) -> str:
    if not values:
        return '<p class="muted">No explainability notes recorded.</p>'
    return '<ul>' + ''.join(f'<li>{_e(value)}</li>' for value in values) + '</ul>'


def _trace_steps(steps: list[dict[str, Any]]) -> str:
    if not steps:
        return '<p class="muted">No explainability trace recorded.</p>'
    return '<ul class="trace-list">' + ''.join(
        f'<li><b>{_e(step.get("stage"))}</b> · <span class="badge {_badge_class(str(step.get("status") or ""))}">{_e(step.get("status"))}</span><div class="hint">{_e(step.get("detail"))}</div></li>'
        for step in steps
    ) + '</ul>'


def _history_rows(history: dict[str, Any] | None, limit: int = 200) -> str:
    items = list((history or {}).get("items") or [])[-limit:]
    if not items:
        return '<tr><td colspan="11" class="muted">No historical reviews recorded.</td></tr>'
    rendered = []
    for item in reversed(items):
        status = str(item.get("status") or "OPEN")
        cls = "status-resolved" if status == "RESOLVED" else "status-open"
        rendered.append(f"""
        <tr>
          <td><span class="{cls}">{_e(status)}</span></td>
          <td>{_e(item.get('history_key') or '')}</td>
          <td>{_e(item.get('server') or '')}</td>
          <td>{_e(item.get('ranking_type') or '')}</td>
          <td>{_e(item.get('rank') or '')}</td>
          <td>{_e(item.get('problem_type') or '')}</td>
          <td>{_e(item.get('problem_statement') or '')}</td>
          <td>{_e(item.get('screenshot') or '')}</td>
          <td>{_e(item.get('seen_count') or 1)}</td>
          <td>{_e(item.get('created_at') or '')}</td>
          <td>{_e(item.get('last_seen_at') or '')}</td>
          <td>{_e((item.get('resolution') or {}).get('selected_choice') or (item.get('resolution') or {}).get('manual_value') or '')}</td>
          <td>{_e((item.get('resolution') or {}).get('comment') or '')}</td>
        </tr>
        """)
    return ''.join(rendered)


def _review_center_cards(import_report: dict[str, Any]) -> str:
    items = _evidence_items(import_report)
    if not items:
        return '<section class="card"><p class="muted">No open review items.</p></section>'
    rendered = []
    for item in items:
        rendered.append(f"""
        <section class="card evidence-card" id="center-{_e(item.get('id'))}">
          <div class="row between"><h3>{_e(item.get('id'))} · {_e(item.get('problem_label'))}</h3><span class="badge warn">OPEN</span></div>
          <div class="action"><b>Problem:</b> {_e(item.get('problem_statement'))}</div>
          <details open><summary>Warum?</summary>{_bullet_list(item.get('why_bullets') or [])}</details>
          <details><summary>Entscheidungspfad</summary>{_trace_steps(item.get('explainability_steps') or [])}</details>
          <details open><summary>Optionen</summary><div class="table-wrap small"><table><thead><tr><th>Option</th><th>Value</th><th>Score</th><th>Reason</th></tr></thead><tbody>{_choice_rows(item)}</tbody></table></div></details>
          <div class="decision"><b>Nächster Schritt:</b> Im Web Review Center kann diese Entscheidung als RESOLVED gespeichert werden. Die statische Karte bleibt reine Evidence-Ansicht.</div>
        </section>
        """)
    return ''.join(rendered)


def render_review_center(import_report: dict[str, Any] | None, history: dict[str, Any] | None) -> str:
    report = import_report or {}
    status = report.get("status") or "No report"
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    open_count = (history or {}).get("open_count", report.get("review_item_count", 0))
    resolved_count = (history or {}).get("resolved_count", 0)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sentinel Review Center</title><style>{_base_css()}</style></head>
<body><header><h1>Sentinel Review Center</h1><div class="muted">Generated {generated_at} · <span class="badge {_badge_class(status)}">{_e(status)}</span></div>
<div class="links"><a href="command_center.html">Command Center</a><a href="review_dashboard.html">Review Queue</a><a href="review_evidence_pack.html">Review Detail / Evidence</a></div></header><main>
<section class="grid">
{_metric_card('Open Reviews', open_count, 'persistent review history')}
{_metric_card('Resolved Reviews', resolved_count, 'manual resolution foundation')}
{_metric_card('Current Run Items', report.get('review_item_count', 0), 'latest report')}
{_metric_card('Readiness', report.get('readiness', 'n/a'), 'operational gate')}
</section>
<div class="tabs"><a href="#open">Open Reviews</a><a href="#history">History</a><a href="command_center.html">Back to Command Center</a></div>
<div class="notice">The static Review Center remains a run-detail view. Interactive resolution is available through the web Review Center (/reviews), where decisions are stored in persistent review history without changing Operational Truth.</div>
<h2 id="open">Open Reviews</h2>{_review_center_cards(report)}
<h2 id="history">Review History</h2><div class="table-wrap"><table><thead><tr><th>Status</th><th>Key</th><th>Server</th><th>Ranking</th><th>Rank</th><th>Type</th><th>Problem</th><th>Screenshot</th><th>Seen</th><th>Created</th><th>Last Seen</th><th>Resolution</th><th>Comment</th></tr></thead><tbody>{_history_rows(history)}</tbody></table></div>
</main></body></html>"""


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
<h2>Review Center</h2><section class="card"><b>Human-in-the-loop review workspace</b><p class="muted">Open review items, review history, and explainability traces are available in the integrated Review Center.</p><div class="links"><a href="review_center.html">Open Review Center</a><a href="review_evidence_pack.html">Open Review Detail / Evidence</a><a href="review_dashboard.html">Open Review Queue</a></div></section>
<h2>Recent Review Items</h2><div class="table-wrap"><table><thead><tr><th>Evidence</th><th>Server</th><th>Ranking</th><th>Rank</th><th>Title</th><th>Reason</th><th>Review OCR</th><th>Row Recon</th><th>Score</th><th>Screenshot</th><th>Description</th></tr></thead><tbody>{_review_rows(report, limit=30)}</tbody></table></div>
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
<h2>All Review Items</h2><div class="table-wrap"><table><thead><tr><th>Evidence</th><th>Server</th><th>Ranking</th><th>Rank</th><th>Title</th><th>Reason</th><th>Review OCR</th><th>Row Recon</th><th>Score</th><th>Screenshot</th><th>Description</th></tr></thead><tbody>{_review_rows(report)}</tbody></table></div>
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
    evidence_payload = _evidence_json(import_report)

    history_path = Path(import_report_path).parent / "review_history.json"
    existing_history = _load_json(history_path)
    history_payload = _history_payload(existing_history, evidence_payload)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(json.dumps(history_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    command_center = output_path / "command_center.html"
    review_center = output_path / "review_center.html"
    review_dashboard = output_path / "review_dashboard.html"
    review_evidence_pack = output_path / "review_evidence_pack.html"
    review_evidence_json = output_path / "review_evidence_pack.json"
    review_history_json = output_path / "review_history.json"
    command_center.write_text(render_command_center(import_report, ground_truth, inference), encoding="utf-8")
    review_center.write_text(render_review_center(import_report, history_payload), encoding="utf-8")
    review_dashboard.write_text(render_review_dashboard(import_report), encoding="utf-8")
    review_evidence_pack.write_text(render_review_evidence_pack(import_report), encoding="utf-8")
    review_evidence_json.write_text(json.dumps(evidence_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    review_history_json.write_text(json.dumps(history_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "command_center": str(command_center),
        "review_center": str(review_center),
        "review_dashboard": str(review_dashboard),
        "review_evidence_pack": str(review_evidence_pack),
        "review_evidence_json": str(review_evidence_json),
        "review_history_json": str(review_history_json),
        "review_history_store": str(history_path),
    }
