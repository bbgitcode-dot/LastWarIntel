"""
LastWarIntel
Sorting Utilities
Version: 1.0
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def top_n(
    values: list[T],
    n: int,
) -> list[T]:
    """
    Returns the first N elements.
    """

    return values[:n]


def sort_descending(
    values: list[T],
    key: Callable[[T], object],
) -> list[T]:
    """
    Sorts descending by key.
    """

    return sorted(
        values,
        key=key,
        reverse=True,
    )