"""
LastWarIntel
Web Application

Application entry point.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from web.routes.alliance import router as alliance_router
from web.routes.dashboard import router as dashboard_router

app = FastAPI(
    title="LastWarIntel",
    version="1.0",
)

app.mount(
    "/static",
    StaticFiles(directory="web/static"),
    name="static",
)

app.include_router(dashboard_router)
app.include_router(alliance_router)