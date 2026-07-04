from pathlib import Path
import pandas as pd

from parser.excel import export
from parser.identity_guard import evaluate_identity_fidelity


def test_operational_export_excludes_pending_review_rows(tmp_path: Path):
    out = tmp_path / "export.xlsx"
    grouped = {
        (551, "total_hero_power"): [
            {"rank": 1, "name": "[PBC] Joncollins21", "power": 416_693_161},
            {"rank": 102, "name": "PENDING REVIEW | Kg Thunder", "power": 25_009_089, "pending_review": True},
        ],
        ("REVIEW", "ranking_guard_quarantine"): [
            {"rank": 1, "name": "Kg Thunder", "power": 25_009_089, "ranking_type": "total_hero_power"},
        ],
    }

    export(grouped, filename=out)
    normal = pd.read_excel(out, sheet_name="551_total_hero_power")
    review = pd.read_excel(out, sheet_name="REVIEW_ranking_guard_quarantine")

    assert len(normal) == 1
    assert not normal["name"].astype(str).str.startswith("PENDING REVIEW |").any()
    assert len(review) == 1


def test_identity_guard_treats_alliance_tag_case_as_fidelity_risk():
    result = evaluate_identity_fidelity(
        observed_alliance_tag="daY",
        canonical_alliance_tag="DAY",
        observed_player_name="Joncollins21",
    )

    assert result.status == "REVIEW"
    assert result.risk == "high"
    assert "alliance_tag_case_sensitive_difference" in result.warnings


def test_identity_guard_flags_digit_letter_confusables_without_correcting():
    result = evaluate_identity_fidelity(
        observed_alliance_tag="PBC",
        canonical_alliance_tag="PBC",
        observed_player_name="Joncollinszl",
    )

    assert result.status == "WARN"
    assert result.risk == "medium"
    assert "player_name_contains_ocr_confusables" in result.warnings
