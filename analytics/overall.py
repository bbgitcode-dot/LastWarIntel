import argparse

from analytics.scoring.overall import OverallScore


def main(server: int):
    scorer = OverallScore()
    result = scorer.calculate(server)

    print(f"\n========== SERVER {server} OVERALL SCORE ==========\n")
    print(f"Overall Score: {result['overall']}/100\n")

    for detail in result["details"]:
        print(f"{detail.name:<10} {detail.score:>6.2f}/100  {detail.explanation}")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("server", type=int)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main(args.server)