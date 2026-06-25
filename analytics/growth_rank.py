from analytics.scoring.growth import GrowthScore


def format_value(value):
    if value is None:
        return "-"

    sign = "-" if value < 0 else ""
    abs_value = abs(value)

    if abs_value >= 1_000_000_000:
        return f"{sign}{abs_value / 1_000_000_000:.2f}B"
    if abs_value >= 1_000_000:
        return f"{sign}{abs_value / 1_000_000:.2f}M"

    return f"{value:,}".replace(",", ".")


def trend_icon(percent):
    if percent >= 30:
        return "🚀"
    if percent >= 15:
        return "📈"
    if percent >= 5:
        return "↗"
    if percent > -5:
        return "➖"
    if percent > -15:
        return "📉"
    return "💀"


def print_section(title, rows):
    print(f"\n========== {title} ==========\n")
    print(f"{'#':>2}  {'Server':<8} {'Score':>7} {'Growth':>10} {'Diff':>10}  Trend")
    print("-" * 58)

    for idx, result in enumerate(rows, start=1):
        print(
            f"{idx:>2}. "
            f"{result['server']:<8} "
            f"{result['score']:>7.2f} "
            f"{result['percent']:>+9.2f}% "
            f"{format_value(result['diff']):>10}  "
            f"{trend_icon(result['percent'])}"
        )


def main():
    scorer = GrowthScore()

    servers = scorer.db.execute(
        """
        SELECT DISTINCT server
        FROM snapshots
        ORDER BY server
        """
    )

    results = []

    for row in servers:
        result = scorer.calculate(row["server"])
        if result:
            results.append(result)

    results.sort(key=lambda x: x["score"], reverse=True)

    print_section("SERVER GROWTH RANKING - TOP 20", results[:20])
    print_section("SERVER GROWTH RANKING - BOTTOM 10", results[-10:])


if __name__ == "__main__":
    main()