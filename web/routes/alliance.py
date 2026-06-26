"""
Alliance Intelligence File Routes
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from analytics.application.entity_report_builder import EntityReportBuilder

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
    report = EntityReportBuilder().build(
        server=server,
        alliance=alliance,
    )

    return templates.TemplateResponse(
        request=request,
        name="alliance.html",
        context={
            "report": report,
        },
    )