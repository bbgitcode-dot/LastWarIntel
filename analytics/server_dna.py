import argparse

from analytics.scoring.overall import OverallScore


def trait_from_score(name: str, score: float):
    if name == "growth":
        if score >= 85:
            return "🚀 Explosive Growth"
        if score >= 65:
            return "📈 Growing"
        if score >= 45:
            return "➖ Moderate Growth"
        return "📉 Weak Growth"

    if name == "power":
        if score >= 85:
            return "💪 Powerhouse"
        if score >= 65:
            return "🟢 Strong"
        if score >= 45:
            return "🟡 Medium Power"
        return "🔴 Low Power"

    return None


def recommendation_from_overall(score: float):
    if score >= 85:
        return "★★★★★ Excellent Transfer Target"
    if score >= 70:
        return "★★★★☆ Strong Transfer Target"
    if score >= 55:
        return "★★★☆☆ Situational Target"
    if score >= 40:
        return "★★☆☆☆ Risky Target"
    return "★☆☆☆☆ Avoid unless there are special reasons"


def risk_from_score(score: float):
    if score >= 75:
        return "LOW"
    if score >= 55:
        return "MEDIUM"
    return "HIGH"


def print_server_dna(server: int):
    scorer = OverallScore()
    result = scorer.calculate(server)

    overall = result["overall"]

    print(f"\n========== SERVER {server} DNA ==========\n")
    print(f"Overall Intel Score: {overall}/100")
    print(f"Risk Level:          {risk_from_score(overall)}")
    print(f"Recommendation:      {recommendation_from_overall(overall)}")

    print("\nTraits:")
    for detail in result["details"]:
        trait = trait_from_score(detail.name, detail.score)
        if trait:
            print(f"  {trait:<25} {detail.score:.2f}/100")

    print("\nWhy:")
    for detail in result["details"]:
        print(f"  - {detail.explanation}")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("server", type=int)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print_server_dna(args.server)