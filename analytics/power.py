import argparse

from analytics.scoring.power import PowerScore


def format_value(value):
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    return str(value)


def main(server: int):
    scorer = PowerScore()
    result = scorer.calculate(server)

    print(f"\n========== SERVER {server} POWER SCORE ==========\n")
    print(f"Top10 Power: {format_value(result.raw_value) if result.raw_value else '-'}")
    print(f"Score:       {result.score}/100")
    print(f"Note:        {result.explanation}")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("server", type=int)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main(args.server)