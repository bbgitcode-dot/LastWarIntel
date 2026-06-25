import argparse

from analytics.scoring.player import PlayerScore


def format_value(value):
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    return str(value)


def print_player_score(server: int):
    scorer = PlayerScore()
    result = scorer.detailed(server)

    if not result:
        print(f"Nicht genug Player-Daten für Server {server}.")
        return

    print(f"\n========== SERVER {server} PLAYER SCORE ==========\n")
    print(f"Player Score: {result['score']}/100")
    print()
    print(f"Top10 THP:    {format_value(result['sum'])}")
    print(f"Average:      {format_value(result['average'])}")
    print(f"Median:       {format_value(result['median'])}")
    print(f"Highest:      {format_value(result['highest'])}")
    print(f"Lowest:       {format_value(result['lowest'])}")
    print(f"Spread:       {format_value(result['spread'])}")

    print("\nElite Players:")
    print(f"  >=300M: {result['elite300']}")
    print(f"  >=320M: {result['elite320']}")
    print(f"  >=350M: {result['elite350']}")

    print("\nTop10 Players:")
    for player in result["players"]:
        tag = player["tag"] or ""
        print(
            f"  #{player['rank']:<2} "
            f"[{tag}] {player['name']:<20} "
            f"{format_value(player['value'])}"
        )


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("server", type=int)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print_player_score(args.server)