"""
LastWarIntel
Module: Recruitment Intelligence
Version: 2.0

Purpose:
    Identify servers that may be worth active recruitment attention.

Important:
    This module does not measure "best server".
    It measures "recruitment opportunity".
"""

from dataclasses import dataclass
from typing import List

from analytics.scoring.growth import GrowthScore
from analytics.scoring.stability import StabilityScore
from analytics.scoring.overall import OverallScore
from services.server_repository import ServerRepository


def format_percent(value):
    if value is None:
        return "-"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}%"


@dataclass
class RecruitmentResult:
    server: int
    score: float
    opportunity: str
    volatility: float
    growth_percent: float
    overall: float
    reasons: List[str]
    warnings: List[str]


@dataclass
class HistoricalDeclineResult:
    server: int
    growth_percent: float
    reason: str


class RecruitmentAnalyzer:
    """
    Recruitment v2.

    Active targets:
        Servers with complete current S6 data and meaningful recruitment signals.

    Historical watchlist:
        Servers that declined historically but lack current S6 comparison data.
    """

    def __init__(self):
        self.repo = ServerRepository()
        self.growth = GrowthScore()
        self.stability = StabilityScore()
        self.overall = OverallScore()

    def analyze_server(self, server: int) -> RecruitmentResult:
        growth_result = self.growth.calculate(server)
        stability_result = self.stability.calculate(server)
        overall_result = self.overall.calculate(server)

        growth_percent = growth_result.raw_value or 0.0
        volatility = stability_result.raw_value or 0.0
        overall_score = overall_result["overall"]

        volatility_component = self._volatility_component(volatility)
        decline_component = self._decline_component(growth_percent)
        relevance_component = self._relevance_component(overall_score)

        score = (
            volatility_component * 0.40
            + decline_component * 0.35
            + relevance_component * 0.25
        )

        reasons = self._build_reasons(volatility, growth_percent, overall_score)
        warnings = self._build_warnings(volatility, growth_percent, overall_score)

        return RecruitmentResult(
            server=server,
            score=round(score, 2),
            opportunity=self._classify_opportunity(score),
            volatility=volatility,
            growth_percent=growth_percent,
            overall=overall_score,
            reasons=reasons,
            warnings=warnings,
        )

    def active_targets(self) -> List[RecruitmentResult]:
        results = []

        for row in self.repo.get_all_servers():
            server = row["server"]

            if not self.repo.has_complete_scoring_data(server):
                continue

            results.append(self.analyze_server(server))

        results.sort(key=lambda item: item.score, reverse=True)
        return results

    def historical_decline_watchlist(self) -> List[HistoricalDeclineResult]:
        results = []

        for row in self.repo.get_all_servers():
            server = row["server"]

            if self.repo.has_complete_scoring_data(server):
                continue

            if not self.repo.has_growth_data(server):
                continue

            growth_result = self.growth.calculate(server)
            growth_percent = growth_result.raw_value or 0.0

            if growth_percent < -10:
                results.append(
                    HistoricalDeclineResult(
                        server=server,
                        growth_percent=growth_percent,
                        reason=(
                            "Historical Top10 alliance power declined strongly, "
                            "but current S6 data is missing."
                        ),
                    )
                )

        results.sort(key=lambda item: item.growth_percent)
        return results

    @staticmethod
    def _volatility_component(volatility: float) -> float:
        if volatility <= 0:
            return 0.0
        if volatility >= 20:
            return 100.0
        return (volatility / 20) * 100

    @staticmethod
    def _decline_component(growth_percent: float) -> float:
        if growth_percent >= 0:
            return 0.0
        decline = abs(growth_percent)
        if decline >= 25:
            return 100.0
        return (decline / 25) * 100

    @staticmethod
    def _relevance_component(overall: float) -> float:
        if overall <= 30:
            return 0.0
        if overall >= 75:
            return 100.0
        return ((overall - 30) / 45) * 100

    @staticmethod
    def _classify_opportunity(score: float) -> str:
        if score >= 80:
            return "★★★★★ Hot Target"
        if score >= 65:
            return "★★★★☆ Strong Opportunity"
        if score >= 50:
            return "★★★☆☆ Potential Target"
        if score >= 35:
            return "★★☆☆☆ Observation"
        return "★☆☆☆☆ Low Priority"

    @staticmethod
    def _build_reasons(volatility: float, growth_percent: float, overall: float) -> List[str]:
        reasons = []

        if volatility >= 15:
            reasons.append("High server volatility suggests internal movement or restructuring.")
        elif volatility >= 8:
            reasons.append("Moderate volatility detected; server may have active movement.")

        if growth_percent < -15:
            reasons.append("Strong negative growth may indicate frustration or alliance losses.")
        elif growth_percent < 0:
            reasons.append("Negative growth detected.")

        if overall >= 70:
            reasons.append("Server remains strong enough to be worth active diplomatic attention.")
        elif overall >= 55:
            reasons.append("Server has enough quality to be monitored.")

        if not reasons:
            reasons.append("No strong recruitment opportunity signal detected yet.")

        return reasons

    @staticmethod
    def _build_warnings(volatility: float, growth_percent: float, overall: float) -> List[str]:
        warnings = []

        if overall < 40:
            warnings.append("Low overall quality; may not be worth heavy recruiting effort.")

        if growth_percent > 15 and volatility < 8:
            warnings.append("Server is growing and relatively stable; recruitment opportunity may be limited.")

        if volatility >= 18 and overall < 55:
            warnings.append("Volatility is high, but server quality is only moderate.")

        return warnings


def print_active_targets(results: List[RecruitmentResult]) -> None:
    print()
    print("========== ACTIVE RECRUITMENT TARGETS ==========")
    print()
    print(
        f"{'#':>2}  "
        f"{'Server':<8} "
        f"{'Score':>7} "
        f"{'Volatility':>11} "
        f"{'Growth':>9} "
        f"{'Overall':>8}  "
        f"Opportunity"
    )
    print("-" * 95)

    if not results:
        print("No active recruitment targets found.")
        return

    for idx, item in enumerate(results, start=1):
        print(
            f"{idx:>2}. "
            f"{item.server:<8} "
            f"{item.score:>7.2f} "
            f"{item.volatility:>10.2f}% "
            f"{format_percent(item.growth_percent):>9} "
            f"{item.overall:>8.2f}  "
            f"{item.opportunity}"
        )

        for reason in item.reasons:
            print(f"     + {reason}")

        for warning in item.warnings:
            print(f"     ! {warning}")

        print()


def print_historical_watchlist(results: List[HistoricalDeclineResult], limit: int = 20) -> None:
    print()
    print("========== HISTORICAL DECLINE WATCHLIST ==========")
    print()
    print("These servers declined historically but do not have complete current S6 data.")
    print("Treat them as leads for manual validation, not as direct active targets.")
    print()
    print(f"{'#':>2}  {'Server':<8} {'Historical Growth':>18}  Reason")
    print("-" * 90)

    if not results:
        print("No historical decline candidates found.")
        return

    for idx, item in enumerate(results[:limit], start=1):
        print(
            f"{idx:>2}. "
            f"{item.server:<8} "
            f"{format_percent(item.growth_percent):>18}  "
            f"{item.reason}"
        )


def main():
    analyzer = RecruitmentAnalyzer()

    active = analyzer.active_targets()
    historical = analyzer.historical_decline_watchlist()

    print_active_targets(active)
    print_historical_watchlist(historical)


if __name__ == "__main__":
    main()
