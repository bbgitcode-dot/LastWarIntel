import argparse
from services.server_service import ServerService


def format_value(value):
    if value is None:
        return "-"

    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"

    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"

    return str(value)


def print_server_report(server: int):
    service = ServerService()
    data = service.get_server_overview(server)

    print(f"\n========== SERVER {server} ==========\n")

    print("Collections:")
    for row in data["collections"]:
        print(f"  - {row['name']} ({row['type']})")

    print("\nAlliance Power:")
    for row in data["alliances"]:
        tag = f"[{row['tag']}]" if row["tag"] else ""
        print(
            f"  {row['collection']} | "
            f"#{row['rank']} {tag} {row['name']} "
            f"{format_value(row['value'])}"
        )

    print("\nTop THP:")
    for row in data["players"]:
        tag = f"[{row['tag']}]" if row["tag"] else ""
        print(
            f"  {row['collection']} | "
            f"#{row['rank']} {tag} {row['name']} "
            f"{format_value(row['value'])}"
        )

    print("\nMetrics:")
    for row in data["metrics"]:
        print(
            f"  {row['collection']} | "
            f"{row['metric_name']}: {format_value(row['value'])}"
        )

    print("\nCities:")
    for row in data["cities"]:
        print(
            f"  {row['alliance']} | "
            f"L1={row['city_level_1']} "
            f"L2={row['city_level_2']} "
            f"L3={row['city_level_3']} "
            f"Influence={format_value(row['influence_points'])}"
        )

    print("\nInfluence:")
    for row in data["influence"]:
        print(
            f"  {row['alliance']} | "
            f"{row['metric_name']}: {format_value(row['value'])}"
        )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Show LastWarIntel server report."
    )
    parser.add_argument("server", type=int)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print_server_report(args.server)