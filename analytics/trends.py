import argparse
from collections import defaultdict

from services.server_service import ServerService


COLLECTION_ORDER = {
    "S4 Server Summary": 1,
    "S5 Pre Transfer": 2,
    "S5 Post Transfer": 3,
    "S6 Preseason Alliances": 4,
}


def format_value(value):
    if value is None:
        return "-"

    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"

    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"

    return f"{value:,}".replace(",", ".")


def format_change(old, new):
    diff = new - old
    percent = (diff / old) * 100 if old else 0

    sign = "+" if diff >= 0 else ""

    return f"{sign}{format_value(diff)} ({sign}{percent:.2f}%)"


def alliance_trends(server: int):
    service = ServerService()
    data = service.get_server_overview(server)

    grouped = defaultdict(list)

    for row in data["alliances"]:
        key = row["tag"] or row["name"]
        grouped[key].append(row)

    print(f"\n========== SERVER {server} ALLIANCE TRENDS ==========\n")

    for key in sorted(grouped.keys()):

        rows = sorted(
            grouped[key],
            key=lambda r: COLLECTION_ORDER.get(r["collection"], 999),
        )

        if len(rows) < 2:
            continue

        print(f"[{key}] {rows[-1]['name']}")

        first_value = rows[0]["value"]
        previous_value = None

        for row in rows:

            value = row["value"]

            if previous_value is None:
                print(
                    f"  {row['collection']:<28} {format_value(value)}"
                )
            else:
                print(
                    f"  {row['collection']:<28} "
                    f"{format_value(value):>10}   {format_change(previous_value, value)}"
                )

            previous_value = value

        print(
            f"  {'Gesamt':<28} {format_change(first_value, rows[-1]['value'])}"
        )

        print("-" * 60)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("server", type=int)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    alliance_trends(args.server)