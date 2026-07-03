"""Review Center routes."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from web.navigation import NAVIGATION, COMMAND_WORKFLOW

router = APIRouter(tags=["reviews"])
templates = Jinja2Templates(directory="web/templates")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _history_path() -> Path:
    return Path("data/review_history.json")


def _screenshot_url(filename: str | None) -> str:
    """Return a safe browser URL for a source screenshot.

    Review data stores screenshot filenames only. Keep this route source-local and
    do not allow path traversal through persisted review JSON.
    """
    name = Path(str(filename or "")).name
    if not name:
        return ""
    return f"/screenshots/{name}"


_RANK_OVERLAY_PROFILES: dict[str, dict[str, float]] = {
    # Calibrated against the current Last War ranking screenshots.  Percentages
    # are relative to the full screenshot image, not the browser card.
    # v0.9.5.64 used a too-low first-row anchor which placed alliance rank 1
    # around visual rank 3; these profiles use the real table row origin.
    "alliance_power": {"top": 13.85, "step": 8.05, "height": 7.45, "left": 2.5, "right": 2.5},
    "total_hero_power": {"top": 13.80, "step": 8.00, "height": 7.45, "left": 2.5, "right": 2.5},
}


def _format_number(value: Any) -> str:
    """Format a numeric value for human review without changing stored data."""
    if value in (None, ""):
        return ""
    try:
        return f"{int(value):,}".replace(",", ".")
    except (TypeError, ValueError):
        return str(value)


def _rank_highlight_meta(item: dict[str, Any]) -> dict[str, Any]:
    """Return calibrated screenshot overlay metadata for the reviewed row.

    The label may show a global visible rank only when Sentinel has actually
    proven one.  For source-row-only reviews the overlay still highlights the
    row, but the label says Row N instead of falsely claiming Rank N.
    """
    source_row_only = item.get("rank_trace_source") == "source_row_only"
    visible_rank = item.get("visible_rank")
    if not source_row_only and visible_rank in (None, ""):
        visible_rank = item.get("rank")
    source_row = item.get("source_row") or item.get("raw_review_rank") or item.get("target_rank")
    row_rank = visible_rank or source_row
    source_row_only = source_row_only or visible_rank in (None, "")
    is_approximate = False
    window = item.get("screenshot_rank_window")
    if isinstance(window, dict):
        try:
            start = int(window.get("start") or 0)
            end = int(window.get("end") or 0)
            vr = int(visible_rank or 0)
            if start and end and start <= vr <= end:
                row_rank = vr - start + 1
            elif item.get("raw_review_rank") not in (None, ""):
                row_rank = int(item.get("raw_review_rank"))
                is_approximate = not source_row_only
        except (TypeError, ValueError):
            pass
    elif item.get("raw_review_rank") not in (None, "") and item.get("rank_trace_source") == "derived_from_screenshot_window":
        try:
            row_rank = int(item.get("raw_review_rank"))
        except (TypeError, ValueError):
            pass

    try:
        row_rank_i = int(row_rank or 0)
    except (TypeError, ValueError):
        row_rank_i = 0
    if row_rank_i <= 0:
        return {"style": "", "label": "", "is_approximate": True}

    ranking_type = str(item.get("ranking_type") or "").lower()
    profile = _RANK_OVERLAY_PROFILES.get(
        ranking_type,
        {"top": 13.80, "step": 8.00, "height": 7.20, "left": 2.5, "right": 2.5},
    )
    top_pct = profile["top"] + (row_rank_i - 1) * profile["step"]
    height_pct = profile["height"]

    if top_pct < 4.0 or top_pct > 88.0:
        is_approximate = True
    top_pct = max(4.0, min(top_pct, 88.0))
    height_pct = max(4.0, min(height_pct, 10.0))
    left_pct = max(0.0, min(profile.get("left", 2.5), 20.0))
    right_pct = max(0.0, min(profile.get("right", 2.5), 20.0))
    style = f"top:{top_pct:.2f}%;height:{height_pct:.2f}%;left:{left_pct:.2f}%;right:{right_pct:.2f}%;"
    label_rank = visible_rank
    if label_rank not in (None, ""):
        label = f"Rank {label_rank}" + (" approx." if is_approximate else "")
    else:
        label = f"OCR Row {row_rank_i}" + (" approx." if is_approximate else "")
    return {"style": style, "label": label, "is_approximate": is_approximate}


def _rank_highlight_style(item: dict[str, Any]) -> str:
    """Backward-compatible helper used by smoke tests and templates."""
    return str(_rank_highlight_meta(item).get("style") or "")


def _enrich_review_item(item: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(item)
    enriched["screenshot_url"] = _screenshot_url(enriched.get("screenshot"))
    highlight = _rank_highlight_meta(enriched)
    enriched["rank_highlight_style"] = highlight.get("style") or ""
    enriched["rank_highlight_label"] = highlight.get("label") or ""
    enriched["rank_highlight_is_approximate"] = bool(highlight.get("is_approximate"))

    source_row_only = enriched.get("rank_trace_source") == "source_row_only"
    visible_rank = enriched.get("visible_rank")
    enriched["display_rank"] = "" if source_row_only else (visible_rank or "")
    enriched["source_row_display"] = enriched.get("source_row") or enriched.get("raw_review_rank") or enriched.get("target_rank") or ""

    # v0.9.5.81: Review surfaces separate raw OCR evidence from Sentinel's
    # operational mapping hypothesis.  A screenshot-local source row is not a
    # proven rank and must never be rendered as one.
    if enriched.get("display_rank"):
        enriched["rank_display_label"] = f"Operational Rank {enriched['display_rank']}"
        enriched["operational_rank_display"] = str(enriched["display_rank"])
        enriched["operational_mapping_status"] = "Mapped to visible ranking position"
    else:
        row = enriched.get("source_row_display") or "unresolved"
        enriched["rank_display_label"] = f"OCR Row {row} · Operational Rank unresolved"
        enriched["operational_rank_display"] = "not determined"
        enriched["operational_mapping_status"] = "Ambiguous / pending human review"

    enriched["target_rank_display"] = enriched.get("target_rank") or enriched.get("raw_review_rank") or ""
    enriched["target_name_display"] = enriched.get("target_name") or (enriched.get("trace") or {}).get("name") or ""
    enriched["target_alliance_display"] = enriched.get("target_alliance") or (enriched.get("trace") or {}).get("alliance") or ""
    enriched["target_power_display"] = _format_number(enriched.get("target_power_selected") or enriched.get("power_selected") or enriched.get("power_original"))

    # Aliases with explicit OCR wording. Templates should prefer these names.
    enriched["ocr_source_name_display"] = enriched["target_name_display"]
    enriched["ocr_source_alliance_display"] = enriched["target_alliance_display"]
    enriched["ocr_source_power_display"] = enriched["target_power_display"]
    enriched["ocr_source_row_label"] = f"OCR Row {enriched.get('source_row_display') or 'unresolved'}"

    window = enriched.get("screenshot_rank_window")
    if isinstance(window, dict) and window.get("start") and window.get("end"):
        enriched["screenshot_rank_window_label"] = f"{window.get('start')}-{window.get('end')}"
    else:
        enriched["screenshot_rank_window_label"] = ""
    enriched["power_original_display"] = _format_number(enriched.get("power_original"))
    enriched["best_candidate_display"] = _format_number(enriched.get("best_candidate"))
    enriched["second_candidate_display"] = _format_number(enriched.get("second_candidate"))
    enriched_choices = []
    for choice in enriched.get("choices") or []:
        choice_copy = dict(choice)
        choice_copy["display_value"] = _format_number(choice_copy.get("value"))
        enriched_choices.append(choice_copy)
    enriched["choices"] = enriched_choices
    return enriched


def _enrich_review_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_enrich_review_item(item) for item in items]


def _refresh_counts(history: dict[str, Any]) -> dict[str, Any]:
    items = list(history.get("items") or [])
    history["open_count"] = sum(1 for item in items if item.get("status") == "OPEN")
    history["resolved_count"] = sum(1 for item in items if item.get("status") == "RESOLVED")
    return history


def _choice_by_label_or_value(item: dict[str, Any], selected_choice: str) -> dict[str, Any] | None:
    if not selected_choice:
        return None
    for choice in item.get("choices") or []:
        label = str(choice.get("label") or "")
        value = "" if choice.get("value") is None else str(choice.get("value"))
        if selected_choice == label or selected_choice == value:
            return choice
    return None


def _resolve_review_item(
    history: dict[str, Any],
    history_key: str,
    *,
    selected_choice: str = "",
    manual_value: str = "",
    manual_name: str = "",
    manual_alliance: str = "",
    comment: str = "",
    reviewer: str = "",
) -> tuple[dict[str, Any], bool]:
    """Mark a persistent review as resolved without touching Operational Truth.

    The resolution is an auditable human decision record only.  Export override
    application is intentionally left to a future guarded Manual Override Engine.
    """
    from datetime import datetime, timezone

    items = list(history.get("items") or [])
    for item in items:
        if item.get("history_key") != history_key:
            continue
        choice = _choice_by_label_or_value(item, selected_choice)
        manual_value_clean = "".join(ch for ch in str(manual_value or "") if ch.isdigit())
        resolution = dict(item.get("resolution") or {})
        resolution.update({
            "status": "RESOLVED",
            "selected_choice": choice.get("label") if choice else (selected_choice or None),
            "selected_value": choice.get("value") if choice else None,
            "manual_value": int(manual_value_clean) if manual_value_clean else None,
            "manual_name": manual_name or None,
            "manual_alliance": manual_alliance or None,
            "comment": comment or None,
            "reviewer": reviewer or None,
            "resolved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "resolution_source": "human_review",
        })
        item["status"] = "RESOLVED"
        item["resolution"] = resolution
        item["resolved_at"] = resolution["resolved_at"]
        history["items"] = items
        return _refresh_counts(history), True
    return _refresh_counts(history), False


def _reopen_review_item(history: dict[str, Any], history_key: str) -> tuple[dict[str, Any], bool]:
    items = list(history.get("items") or [])
    for item in items:
        if item.get("history_key") != history_key:
            continue
        resolution = dict(item.get("resolution") or {})
        resolution["status"] = "OPEN"
        resolution["reopened_at"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(timespec="seconds")
        item["status"] = "OPEN"
        item["resolution"] = resolution
        item.pop("resolved_at", None)
        history["items"] = items
        return _refresh_counts(history), True
    return _refresh_counts(history), False


def _review_model() -> dict[str, Any]:
    history = _load_json(Path("data/review_history.json"))
    evidence = _load_json(Path("output/review_evidence_pack.json"))
    current_items = _enrich_review_items(list(evidence.get("items") or []))
    history_items = _enrich_review_items(list(history.get("items") or []))
    open_items = [item for item in history_items if item.get("status") == "OPEN"]
    resolved_items = [item for item in history_items if item.get("status") == "RESOLVED"]
    by_status: dict[str, int] = {}
    for item in history_items:
        status = str(item.get("status") or "OPEN")
        by_status[status] = by_status.get(status, 0) + 1
    return {
        "has_history": bool(history_items),
        "history_path": "data/review_history.json",
        "evidence_path": "output/review_evidence_pack.json",
        "open_count": len(open_items),
        "resolved_count": len(resolved_items),
        "status_counts": by_status,
        "current_items": current_items,
        "open_items": open_items,
        "resolved_items": resolved_items,
        "history_items": history_items[-200:],
        "output_links": [
            {"href": "/static-output/review_center.html", "label": "Static Review Center"},
            {"href": "/static-output/review_evidence_pack.html", "label": "Static Evidence Detail"},
            {"href": "/static-output/review_dashboard.html", "label": "Static Review Queue"},
        ],
    }


def _find_history_item(history_key: str) -> dict[str, Any] | None:
    model = _review_model()
    for item in model.get("history_items") or []:
        if item.get("history_key") == history_key:
            return item
    return None


@router.get("/reviews")
def reviews(request: Request):
    status_filter = request.query_params.get("status", "")
    return templates.TemplateResponse(
        request=request,
        name="reviews.html",
        context={
            "review_model": _review_model(),
            "navigation": NAVIGATION,
            "workflow_navigation": COMMAND_WORKFLOW,
            "active_page": "reviews",
            "status_filter": status_filter,
        },
    )


@router.get("/reviews/{history_key}")
def review_detail(history_key: str, request: Request):
    item = _find_history_item(history_key)
    if item is None:
        return RedirectResponse(url="/reviews", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="review_detail.html",
        context={
            "item": item,
            "navigation": NAVIGATION,
            "workflow_navigation": COMMAND_WORKFLOW,
            "active_page": "reviews",
        },
    )


@router.post("/reviews/{history_key}/resolve")
async def resolve_review(history_key: str, request: Request):
    raw_body = (await request.body()).decode("utf-8", errors="replace")
    parsed_form = parse_qs(raw_body, keep_blank_values=True)

    def field(name: str) -> str:
        values = parsed_form.get(name) or [""]
        return str(values[0] or "")

    history_path = _history_path()
    history = _load_json(history_path)
    updated, found = _resolve_review_item(
        history,
        history_key,
        selected_choice=field("selected_choice"),
        manual_value=field("manual_value"),
        manual_name=field("manual_name"),
        manual_alliance=field("manual_alliance"),
        comment=field("comment"),
        reviewer=field("reviewer"),
    )
    if found:
        _save_json(history_path, updated)
    return RedirectResponse(url="/reviews", status_code=303)


@router.post("/reviews/{history_key}/reopen")
async def reopen_review(history_key: str):
    history_path = _history_path()
    history = _load_json(history_path)
    updated, found = _reopen_review_item(history, history_key)
    if found:
        _save_json(history_path, updated)
    return RedirectResponse(url="/reviews", status_code=303)


@router.get("/api/reviews")
def reviews_api():
    return _review_model()
