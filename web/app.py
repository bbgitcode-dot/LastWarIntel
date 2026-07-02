"""
Sentinel web application.

Application entry point for the Operational Foundation service.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from version import __version__
from web.routes.alliance import router as alliance_router
from web.routes.alliances import router as alliances_router
from web.routes.command_center import router as command_center_router
from web.routes.feed import router as feed_router
from web.routes.imports import router as imports_router
from web.routes.intelligence import router as intelligence_router
from web.routes.players import router as players_router
from web.routes.quality import router as quality_router
from web.routes.reports import router as reports_router
from web.routes.reviews import router as reviews_router
from web.routes.operations import router as operations_router
from web.routes.rankings import router as rankings_router
from web.routes.servers import router as servers_router
from web.routes.settings import router as settings_router
from web.routes.system import router as system_router


def create_app() -> FastAPI:
    """
    Create the Sentinel FastAPI application.

    Keeping application construction in a factory makes the service easier to
    test and prepares Sentinel for dependency injection in the repository and
    quality-service sprints.
    """

    application = FastAPI(
        title="Sentinel",
        version=__version__,
    )

    application.mount(
        "/static",
        StaticFiles(directory="web/static"),
        name="static",
    )

    application.mount(
        "/static-output",
        StaticFiles(directory="output", html=True, check_dir=False),
        name="static-output",
    )

    application.include_router(system_router)
    application.include_router(command_center_router)
    application.include_router(feed_router)
    application.include_router(alliance_router)
    application.include_router(alliances_router)
    application.include_router(servers_router)
    application.include_router(operations_router)
    application.include_router(imports_router)
    application.include_router(quality_router)
    application.include_router(players_router)
    application.include_router(reports_router)
    application.include_router(reviews_router)
    application.include_router(rankings_router)
    application.include_router(intelligence_router)
    application.include_router(settings_router)

    return application


app = create_app()
