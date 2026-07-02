"""Data Quality routes."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from application.command_center.service import CommandCenterService
from application.data_quality.service import DataQualityService
from web.navigation import NAVIGATION, COMMAND_WORKFLOW

router = APIRouter(tags=["quality"])
templates = Jinja2Templates(directory="web/templates")
service = DataQualityService()


@router.get("/quality")
def quality(request: Request):
    quality_model = service.get_dashboard()
    quality_filter = request.query_params.get("filter", "")
    operational_readiness = CommandCenterService().get_command_center().operational_readiness
    current_missing_servers = [item for item in operational_readiness.server_health if item.status == "Missing Data"]
    return templates.TemplateResponse(
        request=request,
        name="quality.html",
        context={
            "quality": quality_model,
            "navigation": NAVIGATION,
            "workflow_navigation": COMMAND_WORKFLOW,
            "active_page": "quality",
            "quality_filter": quality_filter,
            "operational_readiness": operational_readiness,
            "current_missing_servers": current_missing_servers,
        },
    )


@router.get("/api/quality")
def quality_api():
    return service.get_dashboard()
