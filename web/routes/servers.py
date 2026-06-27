"""
Server Overview Routes
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from analytics.services.server_service import ServerService
from web.navigation import NAVIGATION

router = APIRouter()

templates = Jinja2Templates(
    directory="web/templates",
)


@router.get("/servers")
def servers(
    request: Request,
):
    overview = ServerService().overview(
        server=638,
    )

    return templates.TemplateResponse(
        request=request,
        name="servers.html",
        context={
            "overview": overview,
            "navigation": NAVIGATION,
            "active_page": "servers",
        },
    )