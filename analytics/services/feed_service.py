"""
Sentinel
Feed Service
"""

from __future__ import annotations

from application.intelligence_feed.builder import IntelligenceFeedBuilder


class FeedService:
    """
    Provides the curated Intelligence Feed.
    """

    def get_feed(
        self,
    ):
        return IntelligenceFeedBuilder().build()