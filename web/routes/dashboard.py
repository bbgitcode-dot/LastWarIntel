"""
Dashboard Routes
"""

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from application.dashboard.builder import DashboardBuilder

router = APIRouter()

templates = Jinja2Templates(
    directory="web/templates"
)


@router.get("/")
def dashboard(
    request: Request,
):

    dashboard = DashboardBuilder().build(638)

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "dashboard": dashboard,
        },
    )