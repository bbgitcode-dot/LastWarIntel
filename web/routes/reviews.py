"""Review Center routes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from web.navigation import NAVIGATION

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
        "history_items": history_items[-200:],
        "output_links": [
            {"href": "/static-output/review_center.html", "label": "Static Review Center"},
            {"href": "/static-output/review_evidence_pack.html", "label": "Static Evidence Detail"},
            {"href": "/static-output/review_dashboard.html", "label": "Static Review Queue"},
        ],
    }


@router.get("/reviews")
def reviews(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="reviews.html",
        context={
            "review_model": _review_model(),
            "navigation": NAVIGATION,
            "active_page": "reviews",
        },
    )


@router.get("/api/reviews")
def reviews_api():
    return _review_model()
