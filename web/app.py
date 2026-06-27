"""
Sentinel
Web Application

Application entry point.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from web.routes.alliance import router as alliance_router
from web.routes.alliances import router as alliances_router
from web.routes.dashboard import router as dashboard_router
from web.routes.feed import router as feed_router
from web.routes.intelligence import router as intelligence_router
from web.routes.operations import router as operations_router
from web.routes.rankings import router as rankings_router
from web.routes.servers import router as servers_router
from web.routes.settings import router as settings_router

app = FastAPI(
    title="Sentinel",
    version="1.0",
)

app.mount(
    "/static",
    StaticFiles(directory="web/static"),
    name="static",
)

app.include_router(feed_router)
app.include_router(dashboard_router)
app.include_router(alliance_router)
app.include_router(alliances_router)
app.include_router(servers_router)
app.include_router(operations_router)
app.include_router(rankings_router)
app.include_router(intelligence_router)
app.include_router(settings_router)