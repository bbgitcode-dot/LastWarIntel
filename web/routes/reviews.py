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
    current_items = list(evidence.get("items") or [])
    history_items = list(history.get("items") or [])
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
    return templates.TemplateResponse(
        request=request,
        name="reviews.html",
        context={
            "review_model": _review_model(),
            "navigation": NAVIGATION,
            "workflow_navigation": COMMAND_WORKFLOW,
            "active_page": "reviews",
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
