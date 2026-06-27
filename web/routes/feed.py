"""
Intelligence Feed Routes
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from analytics.services.feed_service import FeedService
from web.navigation import NAVIGATION

router = APIRouter()

templates = Jinja2Templates(
    directory="web/templates",
)


@router.get("/")
def intelligence_feed(
    request: Request,
):
    feed = FeedService().get_feed()

    return templates.TemplateResponse(
        request=request,
        name="feed.html",
        context={
            "feed": feed,
            "navigation": NAVIGATION,
            "active_page": "feed",
        },
    )