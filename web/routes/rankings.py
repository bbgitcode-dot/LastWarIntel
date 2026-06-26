"""
Ranking Routes
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from web.navigation import NAVIGATION

router = APIRouter()

templates = Jinja2Templates(
    directory="web/templates",
)


@router.get("/rankings")
def rankings(
    request: Request,
):
    return templates.TemplateResponse(
        request=request,
        name="coming_soon.html",
        context={
            "title": "Rankings",
            "icon": "📈",
            "navigation": NAVIGATION,
            "active_page": "rankings",
        },
    )