"""Report routes."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from web.navigation import NAVIGATION

router = APIRouter(tags=["reports"])
templates = Jinja2Templates(directory="web/templates")


@router.get("/reports")
def reports(request: Request):
    return templates.TemplateResponse(request=request, name="coming_soon.html", context={"title": "Reports", "icon": "📈", "navigation": NAVIGATION, "active_page": "reports"})
