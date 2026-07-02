"""
Server Routes
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from analytics.services.server_landscape_service import ServerLandscapeService
from analytics.services.server_service import ServerService
from application.command_center.service import CommandCenterService
from application.server_landscape.models import ServerCard, ServerLandscape, ServerState
from application.server_overview.models import ServerOverviewData, ServerOverviewMetric
from web.navigation import NAVIGATION, COMMAND_WORKFLOW

router = APIRouter()
templates = Jinja2Templates(directory="web/templates")


def _fallback_landscape(status_filter: str = "") -> ServerLandscape:
    """Build a safe current-run server landscape when the historical DB is empty.

    The full strategic server landscape requires SQLite tables such as
    ranking_entries.  ZIP baselines and freshly packed workspaces can contain an
    empty database, so drill-down pages must degrade to the current operational
    import/review state instead of raising an internal server error.
    """
    readiness = CommandCenterService().get_command_center().operational_readiness
    cards: list[ServerCard] = []
    wanted = (status_filter or "").lower().replace("_", "-")
    for item in readiness.server_health:
        status = item.status.lower().replace(" ", "-")
        if wanted in {"operational", "ready"} and status != "operational":
            continue
        if wanted in {"pending-review", "open"} and status != "pending-review":
            continue
        if wanted in {"missing-data", "missing"} and status != "missing-data":
            continue
        if wanted in {"failed", "failed-imports"} and status != "import-failed":
            continue
        if item.status == "Operational":
            state = ServerState.READY
            quality = 100.0
            assessment = True
        elif item.status == "Pending Review":
            state = ServerState.PARTIAL
            quality = 75.0
            assessment = False
        elif item.status == "Missing Data":
            state = ServerState.INCOMPLETE
            quality = 40.0
            assessment = False
        else:
            state = ServerState.INCOMPLETE
            quality = 0.0
            assessment = False
        cards.append(
            ServerCard(
                server=item.server,
                state=state,
                dataset_quality=quality,
                activity=0.0,
                recruitability=0.0,
                risk=0.0 if state == ServerState.READY else 65.0,
                last_snapshot="current import/review state",
                summary=item.detail,
                assessment_available=assessment,
            )
        )
    return ServerLandscape(
        cards=cards,
        ready=sum(1 for card in cards if card.state == ServerState.READY),
        partial=sum(1 for card in cards if card.state == ServerState.PARTIAL),
        incomplete=sum(1 for card in cards if card.state == ServerState.INCOMPLETE),
        outdated=sum(1 for card in cards if card.state == ServerState.OUTDATED),
        unknown=sum(1 for card in cards if card.state == ServerState.UNKNOWN),
    )


@router.get("/servers")
def server_landscape(request: Request):
    status_filter = request.query_params.get("status", "")
    try:
        landscape = ServerLandscapeService().get_landscape()
    except Exception:
        landscape = _fallback_landscape(status_filter)
    else:
        if status_filter:
            # Strategic landscape has no current-run status filters. Use the
            # operational fallback for drill-downs so links answer the clicked KPI.
            landscape = _fallback_landscape(status_filter)

    return templates.TemplateResponse(
        request=request,
        name="servers.html",
        context={
            "landscape": landscape,
            "navigation": NAVIGATION,
            "workflow_navigation": COMMAND_WORKFLOW,
            "active_page": "servers",
            "status_filter": status_filter,
        },
    )


@router.get("/servers/{server}")
def server_overview(request: Request, server: int):
    try:
        overview = ServerService().overview(server=server)
    except Exception:
        readiness = CommandCenterService().get_command_center().operational_readiness
        status = "Unknown"
        detail = "No current operational detail found."
        for item in readiness.server_health:
            if item.server == server:
                status = item.status
                detail = item.detail
                break
        overview = ServerOverviewData(
            server=server,
            status=status,
            metrics=[
                ServerOverviewMetric("Dataset", 100.0 if status == "Operational" else 50.0 if status == "Pending Review" else 25.0, "%"),
                ServerOverviewMetric("Recruitment", 0.0, ""),
                ServerOverviewMetric("Strategic Risk", 65.0 if status != "Operational" else 15.0, ""),
                ServerOverviewMetric("Opportunity", 0.0, ""),
            ],
            risks=[detail] if status != "Operational" else [],
            opportunities=[] if status != "Operational" else ["Current import has complete core rankings and no open review for this server."],
            outlook="Fallback overview from current import/review state. Historical intelligence database is empty or unavailable.",
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
