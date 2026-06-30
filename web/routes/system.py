"""
System routes for the Sentinel web service.

These endpoints are intentionally small and dependency-light. They are the
foundation for running Sentinel as a long-lived service instead of only as a
script-driven import pipeline.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter

from version import __version__

router = APIRouter(tags=["system"])

_DATABASE_PATH = Path("data/lastwarintel.sqlite")


def _database_status() -> dict[str, Any]:
    """
    Return a lightweight database health snapshot.

    Commit 1 only verifies that the configured SQLite file is reachable from
    the filesystem. Deeper repository checks belong to the next repository
    sprint.
    """

    exists = _DATABASE_PATH.exists()
    return {
        "status": "ok" if exists else "not_found",
        "path": str(_DATABASE_PATH),
        "exists": exists,
    }


def _system_status() -> dict[str, Any]:
    database = _database_status()
    healthy = database["status"] in {"ok", "not_found"}
    return {
        "application": "Sentinel",
        "version": __version__,
        "status": "healthy" if healthy else "degraded",
        "database": database,
    }


@router.get("/health")
def health() -> dict[str, Any]:
    """
    Human- and automation-friendly health endpoint.
    """

    status = _system_status()
    return {
        "status": status["status"],
        "database": status["database"]["status"],
        "version": status["version"],
    }


@router.get("/version")
def version() -> dict[str, str]:
    """
    Return the running Sentinel version.
    """

    return {
        "application": "Sentinel",
        "version": __version__,
    }


@router.get("/status")
def status() -> dict[str, Any]:
    """
    Return the current operational status snapshot.
    """

    return _system_status()


@router.get("/api/health")
def api_health() -> dict[str, Any]:
    return health()


@router.get("/api/version")
def api_version() -> dict[str, str]:
    return version()


@router.get("/api/status")
def api_status() -> dict[str, Any]:
    return status()
