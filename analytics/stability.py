import argparse

from analytics.scoring.stability import StabilityScore


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


def print_stability(server: int):
    scorer = StabilityScore()
    result = scorer.detailed(server)

    if not result:
        print(f"Nicht genug Daten für Server {server}.")
        return

    print(f"\n========== SERVER {server} STABILITY SCORE ==========\n")

    print(f"Score:       {result['score']}/100")
    print(f"Volatility:  {result['volatility_percent']:.2f}%")
    print(f"Average:     {format_value(result['average_power'])}")
    print(f"Std Dev:     {format_value(result['standard_deviation'])}")

    print("\nTimeline:")
    for row in result["timeline"]:
        print(f"  {row['name']:<28} {format_value(row['total_power'])}")

    print("\nChanges:")
    for change in result["changes"]:
        sign = "+" if change["percent"] >= 0 else ""
        print(
            f"  {change['from']} → {change['to']}: "
            f"{format_value(change['diff'])} "
            f"({sign}{change['percent']:.2f}%)"
        )


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("server", type=int)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print_stability(args.server)