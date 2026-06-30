"""Player routes."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from web.navigation import NAVIGATION

router = APIRouter(tags=["players"])
templates = Jinja2Templates(directory="web/templates")


@router.get("/players")
def players(request: Request):
    return templates.TemplateResponse(request=request, name="coming_soon.html", context={"title": "Players", "icon": "👤", "navigation": NAVIGATION, "active_page": "players"})
