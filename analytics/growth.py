import argparse

from analytics.scoring.growth import GrowthScore


def format_value(value):
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    return str(value)


def print_growth(server: int):
    scorer = GrowthScore()
    result = scorer.detailed(server)

    if not result:
        print(f"Nicht genug Daten für Server {server}.")
        return

    print(f"\n========== SERVER {server} GROWTH SCORE ==========\n")

    for row in result["timeline"]:
        print(f"{row['collection']:<28} {format_value(row['total_power'])}")

    print("\nGrowth:")
    print(f"  {format_value(result['first_power'])} → {format_value(result['last_power'])}")
    print(f"  Diff:    {format_value(result['diff'])}")
    print(f"  Percent: {result['percent']:+.2f}%")
    print(f"  Score:   {result['score']}/100")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("server", type=int)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print_growth(args.server)