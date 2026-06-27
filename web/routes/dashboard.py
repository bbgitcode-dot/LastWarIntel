"""
Dashboard Routes
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from analytics.services.dashboard_service import DashboardService
from web.navigation import NAVIGATION

router = APIRouter()

templates = Jinja2Templates(
    directory="web/templates",
)


@router.get("/")
def dashboard(
    request: Request,
):
    dashboard_data = DashboardService().get_dashboard(
        server=638,
    )

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "dashboard": dashboard_data,
            "navigation": NAVIGATION,
            "active_page": "dashboard",
        },
    )