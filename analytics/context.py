"""
Sentinel Context

Provides contextual information for every analysis.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(slots=True, frozen=True)
class SentinelContext:
    """
    Shared execution context.

    Every analysis within Sentinel should receive the same
    context instead of individual parameters.
    """

    server: int

    campaign: Optional[str] = None

    milestone: Optional[str] = None

    collection_id: Optional[str] = None

    captured_at: Optional[datetime] = None

    uploaded_at: Optional[datetime] = None

    confidence: float = 100.0