"""
Sentinel service entry point.

Run locally with:
    uvicorn sentinel:app --reload
"""

from web.app import app

__all__ = ["app"]
