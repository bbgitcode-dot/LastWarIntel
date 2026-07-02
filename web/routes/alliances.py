"""
Alliance Overview Routes
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from web.navigation import NAVIGATION, COMMAND_WORKFLOW

router = APIRouter()

templates = Jinja2Templates(
    directory="web/templates",
)


@router.get("/alliances")
def alliances(
    request: Request,
):
    return templates.TemplateResponse(
        request=request,
        name="coming_soon.html",
        context={
            "title": "Alliances",
            "icon": "🏰",
            "navigation": NAVIGATION,
            "workflow_navigation": COMMAND_WORKFLOW,
            "active_page": "alliances",
        },
    )