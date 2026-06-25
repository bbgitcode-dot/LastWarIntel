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

    abs_value = abs(value)

    if abs_value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"

    if abs_value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"

    return f"{value:,}".replace(",", ".")


def classify_change(percent):
    if percent >= 20:
        return "🚀 Explosive Growth"
    if percent >= 10:
        return "📈 Strong Growth"
    if percent >= 5:
        return "↗ Growing"
    if percent > -5:
        return "➖ Stable"
    if percent > -15:
        return "📉 Declining"
    return "💀 Heavy Decline"


def calculate_change(old, new):
    diff = new - old
    percent = (diff / old) * 100 if old else 0
    return diff, percent


def build_alliance_history(server: int):
    service = ServerService()
    data = service.get_server_overview(server)

    grouped = defaultdict(list)

    for row in data["alliances"]:
        key = row["tag"] or row["name"]
        grouped[key].append(row)

    histories = {}

    for key, rows in grouped.items():
        rows = sorted(
            rows,
            key=lambda r: COLLECTION_ORDER.get(r["collection"], 999),
        )

        if len(rows) < 2:
            continue

        first = rows[0]
        last = rows[-1]

        diff, percent = calculate_change(first["value"], last["value"])

        step_changes = []

        for idx in range(1, len(rows)):
            previous = rows[idx - 1]
            current = rows[idx]
            step_diff, step_percent = calculate_change(
                previous["value"],
                current["value"],
            )

            step_changes.append(
                {
                    "from": previous["collection"],
                    "to": current["collection"],
                    "diff": step_diff,
                    "percent": step_percent,
                }
            )

        histories[key] = {
            "tag": key,
            "name": last["name"],
            "first_collection": first["collection"],
            "last_collection": last["collection"],
            "first_value": first["value"],
            "last_value": last["value"],
            "diff": diff,
            "percent": percent,
            "classification": classify_change(percent),
            "steps": step_changes,
            "rows": rows,
        }

    return histories


def print_intelligence_report(server: int):
    histories = build_alliance_history(server)

    if not histories:
        print(f"Keine ausreichenden Trenddaten für Server {server}.")
        return

    sorted_by_diff = sorted(
        histories.values(),
        key=lambda item: item["diff"],
        reverse=True,
    )

    sorted_by_percent = sorted(
        histories.values(),
        key=lambda item: item["percent"],
        reverse=True,
    )

    losers = sorted(
        histories.values(),
        key=lambda item: item["diff"],
    )

    print(f"\n========== SERVER {server} INTELLIGENCE REPORT ==========\n")

    print("TOP WINNERS BY POWER")
    print("-" * 55)
    for item in sorted_by_diff[:5]:
        print(
            f"{item['tag']:<8} "
            f"{format_value(item['first_value']):>10} → "
            f"{format_value(item['last_value']):>10} | "
            f"{format_value(item['diff']):>10} | "
            f"{item['percent']:+.2f}% | "
            f"{item['classification']}"
        )

    print("\nTOP WINNERS BY %")
    print("-" * 55)
    for item in sorted_by_percent[:5]:
        print(
            f"{item['tag']:<8} "
            f"{format_value(item['diff']):>10} | "
            f"{item['percent']:+.2f}% | "
            f"{item['classification']}"
        )

    print("\nTOP LOSERS")
    print("-" * 55)
    for item in losers[:5]:
        print(
            f"{item['tag']:<8} "
            f"{format_value(item['first_value']):>10} → "
            f"{format_value(item['last_value']):>10} | "
            f"{format_value(item['diff']):>10} | "
            f"{item['percent']:+.2f}% | "
            f"{item['classification']}"
        )

    print("\nVOLATILITY WATCH")
    print("-" * 55)

    volatility = []

    for item in histories.values():
        if not item["steps"]:
            continue

        max_step = max(abs(step["percent"]) for step in item["steps"])
        volatility.append((max_step, item))

    volatility.sort(key=lambda x: x[0], reverse=True)

    for max_step, item in volatility[:5]:
        print(f"{item['tag']:<8} max step swing: {max_step:.2f}%")
        for step in item["steps"]:
            print(
                f"    {step['from']} → {step['to']}: "
                f"{format_value(step['diff'])} "
                f"({step['percent']:+.2f}%)"
            )

    print("\nCLASSIFICATION")
    print("-" * 55)

    for item in sorted_by_percent:
        print(
            f"{item['tag']:<8} "
            f"{item['percent']:+7.2f}%   "
            f"{item['classification']}"
        )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate LastWarIntel intelligence report."
    )
    parser.add_argument("server", type=int)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print_intelligence_report(args.server)