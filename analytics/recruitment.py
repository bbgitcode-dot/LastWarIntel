from analytics.scoring.growth import GrowthScore
from analytics.scoring.stability import StabilityScore
from analytics.scoring.overall import OverallScore
from services.server_repository import ServerRepository


def format_value(value):
    sign = "-" if value < 0 else ""
    value = abs(value)

    if value >= 1_000_000_000:
        return f"{sign}{value / 1_000_000_000:.2f}B"

    if value >= 1_000_000:
        return f"{sign}{value / 1_000_000:.2f}M"

    return f"{sign}{value}"


def calculate_recruitment_score(server: int):
    growth = GrowthScore().calculate(server)
    stability = StabilityScore().calculate(server)
    overall = OverallScore().calculate(server)

    volatility = stability.raw_value or 0
    growth_percent = growth.raw_value or 0

    # Idee:
    # hohe Volatilität = gute Rekrutierungschance
    # negatives Wachstum = Frustpotenzial
    # mittlere Overall-Qualität = Server ist relevant genug
    volatility_score = min(volatility * 4, 100)

    decline_score = 0
    if growth_percent < 0:
        decline_score = min(abs(growth_percent) * 5, 100)

    relevance_score = overall["overall"]

    score = (
        volatility_score * 0.45
        + decline_score * 0.35
        + relevance_score * 0.20
    )

    reasons = []

    if volatility >= 10:
        reasons.append("high volatility detected")
    if growth_percent < 0:
        reasons.append("server is losing Top10 alliance power")
    if overall["overall"] >= 55:
        reasons.append("server is still relevant enough to target")
    if not reasons:
        reasons.append("limited recruitment opportunity signals")

    return {
        "server": server,
        "score": round(score, 2),
        "volatility": volatility,
        "growth_percent": growth_percent,
        "overall": overall["overall"],
        "reasons": reasons,
    }


def opportunity_icon(score):
    if score >= 80:
        return "🔥"
    if score >= 60:
        return "⚠️"
    if score >= 40:
        return "👀"
    return "➖"


def main():
    repo = ServerRepository()

    servers = repo.get_all_servers()

    results = []

    for row in servers:
        server = row["server"]

        if not repo.has_growth_data(server):
            continue

        result = calculate_recruitment_score(server)
        results.append(result)

    results.sort(key=lambda item: item["score"], reverse=True)

    print("\n========== RECRUITMENT OPPORTUNITY RANKING ==========\n")
    print(f"{'#':>2}  {'Server':<8} {'Score':>7} {'Volatility':>11} {'Growth':>9} {'Overall':>8}  Signal")
    print("-" * 78)

    for idx, item in enumerate(results[:30], start=1):
        print(
            f"{idx:>2}. "
            f"{item['server']:<8} "
            f"{item['score']:>7.2f} "
            f"{item['volatility']:>10.2f}% "
            f"{item['growth_percent']:>+8.2f}% "
            f"{item['overall']:>8.2f}  "
            f"{opportunity_icon(item['score'])}"
        )

        for reason in item["reasons"]:
            print(f"     - {reason}")

        print()


if __name__ == "__main__":
    main()