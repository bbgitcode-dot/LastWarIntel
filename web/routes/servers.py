"""
Server Overview Routes
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from web.navigation import NAVIGATION

router = APIRouter()

templates = Jinja2Templates(
    directory="web/templates",
)


@router.get("/servers")
def servers(
    request: Request,
):
    return templates.TemplateResponse(
        request=request,
        name="coming_soon.html",
        context={
            "title": "Servers",
            "icon": "🗺️",
            "navigation": NAVIGATION,
            "active_page": "servers",
        },
    )