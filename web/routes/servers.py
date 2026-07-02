"""
Server Routes
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from analytics.services.server_landscape_service import (
    ServerLandscapeService,
)
from analytics.services.server_service import ServerService
from web.navigation import NAVIGATION, COMMAND_WORKFLOW

router = APIRouter()

templates = Jinja2Templates(
    directory="web/templates",
)


@router.get("/servers")
def server_landscape(
    request: Request,
):
    landscape = ServerLandscapeService().get_landscape()

    return templates.TemplateResponse(
        request=request,
        name="servers.html",
        context={
            "landscape": landscape,
            "navigation": NAVIGATION,
            "workflow_navigation": COMMAND_WORKFLOW,
            "active_page": "servers",
        },
    )


@router.get("/servers/{server}")
def server_overview(
    request: Request,
    server: int,
):
    overview = ServerService().overview(
        server=server,
    )

    return templates.TemplateResponse(
        request=request,
        name="server_overview.html",
        context={
            "overview": overview,
            "navigation": NAVIGATION,
            "workflow_navigation": COMMAND_WORKFLOW,
            "active_page": "servers",
        },
    )