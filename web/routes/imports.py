"""Import Center routes."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from application.operational_import.service import OperationalImportService
from web.navigation import NAVIGATION, COMMAND_WORKFLOW

router = APIRouter(tags=["imports"])
templates = Jinja2Templates(directory="web/templates")
service = OperationalImportService()


@router.get("/imports")
def imports(request: Request):
    import_model = service.get_dashboard()
    return templates.TemplateResponse(
        request=request,
        name="imports.html",
        context={
            "import_model": import_model,
            "navigation": NAVIGATION,
            "workflow_navigation": COMMAND_WORKFLOW,
            "active_page": "imports",
        },
    )


@router.get("/api/imports")
def imports_api():
    return service.get_dashboard()
