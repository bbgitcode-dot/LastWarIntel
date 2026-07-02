"""Command Center routes."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from application.command_center.service import CommandCenterService
from web.navigation import NAVIGATION, COMMAND_WORKFLOW

router = APIRouter(tags=["command-center"])
templates = Jinja2Templates(directory="web/templates")


@router.get("/")
def command_center(request: Request):
    command = CommandCenterService().get_command_center()
    return templates.TemplateResponse(
        request=request,
        name="command_center.html",
        context={
            "command": command,
            "navigation": NAVIGATION,
            "workflow_navigation": COMMAND_WORKFLOW,
            "active_page": "command",
        },
    )


@router.get("/command")
def command_center_alias(request: Request):
    return command_center(request)
