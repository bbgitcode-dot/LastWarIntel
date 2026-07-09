import json
import pandas as pd

from ground_truth_validator import _apply_display_reconstruction, _build_display_reconstruction_report


def test_display_reconstruction_uses_character_evidence_without_operational_write():
    row = {
        "server": 551,
        "rank": 1,
        "expected_name": "Joncollins21",
        "ocr_name": "Joncollinszl",
        "expected_alliance_display": "PbC",
        "ocr_alliance_display": "PBC",
        "verified_name_display": "Joncollins21",
        "verified_alliance_display": "PBC",
        "verified_name_display_exact_match": True,
        "verified_alliance_display_exact_match": False,
        "alignment_context_gap": False,
        "gold_core_blocker": False,
        "row_integrity_status": "ROW_OK_WITH_CROP_WARNING",
        "character_reocr_evidence": json.dumps([
            {"field": "player_name", "position": 10, "expected": "2", "observed": "z", "status": "verified_expected", "confidence": 1.0},
            {"field": "player_name", "position": 11, "expected": "1", "observed": "l", "status": "verified_expected", "confidence": 1.0},
        ]),
        "read_only_reocr_evidence": "[]",
    }
    detail = _apply_display_reconstruction(pd.DataFrame([row]))

    assert detail.loc[0, "display_reconstructed_name"] == "Joncollins21"
    assert detail.loc[0, "display_reconstruction_status"] == "name_reconstructed"
    assert bool(detail.loc[0, "display_reconstruction_operational_truth_modified"]) is False
    # Existing report/operational display fields remain untouched.
    assert detail.loc[0, "verified_alliance_display"] == "PBC"


def test_display_reconstruction_exposes_context_gap_suggestion_as_read_only():
    row = {
        "server": 551,
        "rank": 21,
        "expected_name": "K9 Thunder 자주포",
        "ocr_name": "显丛显丛 X YUNS",
        "expected_alliance_display": "IVE",
        "ocr_alliance_display": "IVE",
        "verified_name_display": "显丛显丛 X YUNS",
        "verified_alliance_display": "IVE",
        "verified_name_display_exact_match": False,
        "verified_alliance_display_exact_match": False,
        "alignment_context_gap": True,
        "gold_core_blocker": False,
        "row_integrity_status": "ROW_CONTEXT_GAP",
        "read_only_confidence": 0.99,
        "character_reocr_evidence": "[]",
        "read_only_reocr_evidence": json.dumps([
            {"suggested_name_display": "K9 Thunder 자주포", "suggested_alliance_display": "IVE", "status": "executed_read_only_contextual_verification"}
        ]),
    }
    detail = _apply_display_reconstruction(pd.DataFrame([row]))

    assert detail.loc[0, "display_reconstruction_status"] == "contextual_display_suggestion"
    assert detail.loc[0, "display_reconstructed_name"] == "K9 Thunder 자주포"
    assert detail.loc[0, "display_reconstruction_source"] == "read_only_contextual_inference"
    assert bool(detail.loc[0, "display_reconstruction_operational_truth_modified"]) is False


def test_display_reconstruction_report_contains_only_relevant_rows():
    rows = pd.DataFrame([
        {
            "server": 551,
            "rank": 1,
            "expected_name": "Joncollins21",
            "ocr_name": "Joncollinszl",
            "expected_alliance_display": "PbC",
            "ocr_alliance_display": "PBC",
            "verified_name_display": "Joncollins21",
            "verified_alliance_display": "PBC",
            "verified_name_display_exact_match": True,
            "verified_alliance_display_exact_match": False,
            "character_reocr_evidence": json.dumps([
                {"field": "player_name", "position": 10, "expected": "2", "observed": "z", "status": "verified_expected", "confidence": 1.0}
            ]),
            "read_only_reocr_evidence": "[]",
        },
        {
            "server": 551,
            "rank": 4,
            "expected_name": "LOVE BIEN",
            "ocr_name": "LOVE BIEN",
            "expected_alliance_display": "IVE",
            "ocr_alliance_display": "IVE",
            "verified_name_display": "LOVE BIEN",
            "verified_alliance_display": "IVE",
            "verified_name_display_exact_match": True,
            "verified_alliance_display_exact_match": True,
            "character_reocr_evidence": "[]",
            "read_only_reocr_evidence": "[]",
        },
    ])
    detail = _apply_display_reconstruction(rows)
    summary, report = _build_display_reconstruction_report(detail)

    assert len(report) == 2
    assert int(summary["rows"].sum()) == 2
    assert set(report["display_reconstruction_operational_truth_modified"].unique()) == {False}
