from analytics.scoring.overall import OverallScore


def score_icon(score):
    if score >= 90:
        return "🏆"
    if score >= 80:
        return "⭐"
    if score >= 70:
        return "🟢"
    if score >= 60:
        return "🟡"
    if score >= 50:
        return "🟠"
    return "🔴"


def main():
    scorer = OverallScore()

    servers = scorer.scorers[0].db.execute(
        """
        SELECT DISTINCT server
        FROM snapshots
        ORDER BY server
        """
    )

    results = []

    for row in servers:
        result = scorer.calculate(row["server"])
        if result["overall"] > 0:
            results.append(result)

    results.sort(key=lambda item: item["overall"], reverse=True)

    print("\n========== OVERALL SERVER RANKING ==========\n")
    print(f"{'#':>2}  {'Server':<8} {'Overall':>8} {'Growth':>8} {'Power':>8}  Tier")
    print("-" * 58)

    for idx, result in enumerate(results[:30], start=1):
        details = {item.name: item.score for item in result["details"]}

        print(
            f"{idx:>2}. "
            f"{result['server']:<8} "
            f"{result['overall']:>8.2f} "
            f"{details.get('growth', 0):>8.2f} "
            f"{details.get('power', 0):>8.2f}  "
            f"{score_icon(result['overall'])}"
        )


if __name__ == "__main__":
    main()