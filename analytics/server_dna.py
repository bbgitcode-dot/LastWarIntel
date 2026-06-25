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

    if name == "depth":
        if score >= 80:
            return "🌊 Deep Alliance Structure"
        if score >= 60:
            return "🟢 Balanced Alliance Structure"
        if score >= 45:
            return "🟡 Moderate Alliance Structure"
        return "🔴 Top Heavy"

    if name == "player":
        if score >= 85:
            return "👑 Elite Player Base"
        if score >= 65:
            return "👥 Strong Player Base"
        if score >= 45:
            return "🟡 Average Player Base"
        return "🔴 Weak Player Base"

    if name == "stability":
        if score >= 85:
            return "🛡 Extremely Stable"
        if score >= 65:
            return "⚖ Stable"
        if score >= 45:
            return "🟡 Some Volatility"
        return "🌪 Highly Volatile"

    return ""


def recommendation(score):

    if score >= 85:
        return "★★★★★ Excellent Transfer Target"

    if score >= 70:
        return "★★★★☆ Strong Transfer Target"

    if score >= 55:
        return "★★★☆☆ Situational Target"

    if score >= 40:
        return "★★☆☆☆ Risky Target"

    return "★☆☆☆☆ Avoid unless there are special reasons"


def risk(score):

    if score >= 75:
        return "LOW"

    if score >= 55:
        return "MEDIUM"

    return "HIGH"


def print_dna(server):

    result = OverallScore().calculate(server)

    print()
    print(f"========== SERVER {server} DNA ==========")
    print()

    print(f"Overall Intel Score: {result['overall']:.2f}/100")
    print(f"Risk Level:          {risk(result['overall'])}")
    print(f"Recommendation:      {recommendation(result['overall'])}")

    print()
    print("Traits:")

    for score in result["details"]:
        trait = trait_from_score(score.name, score.score)
        print(f"  {trait:<35} {score.score:.2f}/100")

    print()
    print("Why:")

    for score in result["details"]:
        print(f"  - {score.explanation}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("server", type=int)

    args = parser.parse_args()

    print_dna(args.server)


if __name__ == "__main__":
    main()