from analytics.scoring.overall import OverallScore
from analytics.server_dna import (
    recommendation_from_overall,
    risk_from_score,
    trait_from_score,
)


def main():
    scorer = OverallScore()

    servers = scorer.scorers[0].db.execute(
        """
        SELECT DISTINCT s.server
        FROM snapshots s
        JOIN ranking_entries re ON re.snapshot_id = s.id
        JOIN ranking_types rt ON rt.id = re.ranking_type_id
        JOIN collections c ON c.id = s.collection_id
        WHERE rt.name = 'alliance_power'
          AND c.name = 'S6 Preseason Alliances'
        ORDER BY s.server
        """
    )

    results = []

    for row in servers:
        result = scorer.calculate(row["server"])
        results.append(result)

    results.sort(key=lambda item: item["overall"], reverse=True)

    print("\n========== SERVER DNA RANKING ==========\n")
    print(f"{'#':>2}  {'Server':<8} {'Overall':>8} {'Risk':<8} Recommendation")
    print("-" * 80)

    for idx, result in enumerate(results, start=1):
        server = result["server"]
        overall = result["overall"]
        risk = risk_from_score(overall)
        recommendation = recommendation_from_overall(overall)

        print(
            f"{idx:>2}. "
            f"{server:<8} "
            f"{overall:>8.2f} "
            f"{risk:<8} "
            f"{recommendation}"
        )

        traits = []
        for detail in result["details"]:
            trait = trait_from_score(detail.name, detail.score)
            if trait:
                traits.append(trait)

        if traits:
            print(f"    Traits: {', '.join(traits)}")

        print()


if __name__ == "__main__":
    main()