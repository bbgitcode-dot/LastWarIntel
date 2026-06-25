import argparse

from analytics.scoring.depth import DepthScore


def format_value(value):
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    return str(value)


def main(server: int):
    scorer = DepthScore()
    result = scorer.detailed(server)

    if not result:
        print(f"Nicht genug Daten für Server {server}.")
        return

    print(f"\n========== SERVER {server} DEPTH SCORE ==========\n")
    print(f"Score:       {result['score']}/100")
    print(f"Gini:        {result['gini']:.3f}")
    print(f"Top1 Share:  {result['top1_share'] * 100:.2f}%")
    print(f"Top3 Share:  {result['top3_share'] * 100:.2f}%")
    print(f"Top10 Total: {format_value(result['total'])}")

    print("\nTop10 Distribution:")
    for row in result["alliances"]:
        share = row["value"] / result["total"] if result["total"] else 0
        tag = row["tag"] or row["name"]

        print(
            f"  #{row['rank']:<2} "
            f"{tag:<8} "
            f"{format_value(row['value']):>10} "
            f"{share * 100:>6.2f}%"
        )


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("server", type=int)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main(args.server)