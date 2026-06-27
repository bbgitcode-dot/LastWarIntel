"""
Sentinel
Intelligence Provider Registry
"""

from __future__ import annotations

from analytics.intelligence.provider import IntelligenceProvider


class IntelligenceRegistry:
    """
    Holds all registered intelligence providers.
    """

    def __init__(self) -> None:

        self._providers: list[IntelligenceProvider] = []

    def register(
        self,
        provider: IntelligenceProvider,
    ) -> None:

        self._providers.append(provider)

    def providers(
        self,
    ) -> list[IntelligenceProvider]:

        return list(self._providers)