"""Intelligence Feed routes."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from web.navigation import NAVIGATION, COMMAND_WORKFLOW

router = APIRouter(tags=["feed"])
templates = Jinja2Templates(directory="web/templates")


@router.get("/feed")
def intelligence_feed(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="coming_soon.html",
        context={
            "title": "Intelligence Feed",
            "icon": "🧠",
            "navigation": NAVIGATION,
            "workflow_navigation": COMMAND_WORKFLOW,
            "active_page": "intel",
        },
    )
