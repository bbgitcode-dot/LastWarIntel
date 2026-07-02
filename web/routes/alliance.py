"""
Alliance Routes
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from analytics.services.alliance_service import AllianceService
from web.navigation import NAVIGATION, COMMAND_WORKFLOW

router = APIRouter()

templates = Jinja2Templates(
    directory="web/templates",
)


@router.get("/alliance/{server}/{alliance}")
def alliance_file(
    request: Request,
    server: int,
    alliance: str,
):
    report = AllianceService().get_report(
        server=server,
        alliance=alliance,
    )

    return templates.TemplateResponse(
        request=request,
        name="alliance.html",
        context={
            "report": report,
            "navigation": NAVIGATION,
            "workflow_navigation": COMMAND_WORKFLOW,
            "active_page": "alliances",
        },
    )