"""Import Center routes."""

from __future__ import annotations

from fastapi import APIRouter, Request
from urllib.parse import parse_qs
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from application.historical_import.service import HistoricalImportService
from application.operational_import.service import OperationalImportService
from application.snapshots.service import SnapshotContextError, SnapshotService
from web.navigation import NAVIGATION, COMMAND_WORKFLOW

router = APIRouter(tags=["imports"])
templates = Jinja2Templates(directory="web/templates")
service = OperationalImportService()
historical_service = HistoricalImportService()
snapshot_service = SnapshotService()


@router.get("/imports")
def imports(request: Request):
    import_model = service.get_dashboard()
    historical_import = historical_service.get_dashboard()
    snapshot_model = snapshot_service.get_dashboard()
    status_filter = request.query_params.get("status", "")
    snapshot_notice = request.query_params.get("snapshot", "")
    return templates.TemplateResponse(
        request=request,
        name="imports.html",
        context={
            "import_model": import_model,
            "historical_import": historical_import,
            "snapshot_model": snapshot_model,
            "navigation": NAVIGATION,
            "workflow_navigation": COMMAND_WORKFLOW,
            "active_page": "imports",
            "status_filter": status_filter,
            "snapshot_notice": snapshot_notice,
        },
    )


@router.post("/imports/snapshots")
async def create_snapshot(request: Request):
    form = _read_urlencoded(await request.body())
    name = form.get("name", "")
    snapshot_type = form.get("snapshot_type", "screenshot_upload")
    description = form.get("description", "")
    assigned_servers_raw = form.get("assigned_servers", "")
    server_scope_mode = form.get("server_scope_mode", "selected")
    server_range_start = form.get("server_range_start", "")
    server_range_end = form.get("server_range_end", "")
    expected_rankings: list[str] = []
    if form.get("expected_alliance_power"):
        expected_rankings.append("alliance_power")
    if form.get("expected_total_hero_power"):
        expected_rankings.append("total_hero_power")
    try:
        snapshot_service.create_snapshot(
            name=name,
            snapshot_type=snapshot_type,
            description=description,
            expected_rankings=expected_rankings or ["alliance_power", "total_hero_power"],
            source="Import Center",
            assigned_servers=assigned_servers_raw,
            server_scope_mode=server_scope_mode,
            server_range_start=server_range_start,
            server_range_end=server_range_end,
            set_active=True,
        )
        target = "/imports?snapshot=created"
    except ValueError:
        target = "/imports?snapshot=missing-name"
    return RedirectResponse(url=target, status_code=303)


@router.post("/imports/snapshots/{snapshot_id}/activate")
def activate_snapshot(snapshot_id: str):
    snapshot_service.set_active(snapshot_id)
    return RedirectResponse(url="/imports?snapshot=activated", status_code=303)


@router.post("/imports/snapshots/{snapshot_id}/status")
async def update_snapshot_status(snapshot_id: str, request: Request):
    form = _read_urlencoded(await request.body())
    status = form.get("status", "open")
    snapshot_service.update_status(snapshot_id, status)
    return RedirectResponse(url="/imports?snapshot=status-updated", status_code=303)


@router.post("/imports/snapshots/{snapshot_id}/edit")
async def edit_snapshot(snapshot_id: str, request: Request):
    form = _read_urlencoded(await request.body())
    expected_rankings: list[str] = []
    if form.get("expected_alliance_power"):
        expected_rankings.append("alliance_power")
    if form.get("expected_total_hero_power"):
        expected_rankings.append("total_hero_power")
    try:
        snapshot_service.update_snapshot(
            snapshot_id,
            name=form.get("name", ""),
            description=form.get("description", ""),
            expected_rankings=expected_rankings or ["alliance_power", "total_hero_power"],
            server_scope_mode=form.get("server_scope_mode", "selected"),
            assigned_servers=form.get("assigned_servers", ""),
            server_range_start=form.get("server_range_start", ""),
            server_range_end=form.get("server_range_end", ""),
        )
        target = "/imports?snapshot=updated"
    except (ValueError, SnapshotContextError):
        target = "/imports?snapshot=edit-blocked"
    return RedirectResponse(url=target, status_code=303)


@router.get("/api/imports")
def imports_api():
    return service.get_dashboard()


def _read_urlencoded(body: bytes) -> dict[str, str]:
    parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True)
    return {key: values[-1] if values else "" for key, values in parsed.items()}
