import pandas as pd

from ground_truth_validator import (
    _apply_reocr_budget_gate,
    _is_pre_reocr_core_safe,
    _row_evidence_status,
)
from parser.targeted_character_reocr import ReOcrTarget


def test_pre_reocr_core_safe_for_latin_residual_containment():
    safe, reason = _is_pre_reocr_core_safe(
        accepted_match=True,
        name_category="latin_only",
        raw_power_match=True,
        raw_alliance_match=True,
        raw_name_display_exact=False,
        raw_name_normalized_match=False,
        name_normalized_similarity=0.60,
        expected_name_latin_core="Zed",
        actual_name_latin_core="XZed005",
        expected_name_key="ZED",
        actual_name_key="XZEDOOS",
    )
    assert safe is True
    assert reason == "latin_residual_core_preverified"


def test_pre_reocr_core_safe_does_not_skip_joncollins_glyph_repair():
    safe, reason = _is_pre_reocr_core_safe(
        accepted_match=True,
        name_category="latin_only",
        raw_power_match=True,
        raw_alliance_match=True,
        raw_name_display_exact=False,
        raw_name_normalized_match=True,
        name_normalized_similarity=0.9167,
        expected_name_latin_core="Joncollins21",
        actual_name_latin_core="Joncollinszl",
        expected_name_key="JONCOLLINS21",
        actual_name_key="JONCOLLINSZL",
    )
    assert safe is False
    assert reason == "latin_core_not_stable"


def test_budget_gate_skips_core_safe_player_cosmetic_target():
    targets = [
        ReOcrTarget(field="player_name", position=0, expected="x", observed="X", reason="display_character_difference"),
        ReOcrTarget(field="alliance_tag", position=1, expected="b", observed="", reason="ocr_confusable_tag_character_difference", group="8Bb"),
    ]
    kept, skipped, reasons = _apply_reocr_budget_gate(
        targets,
        raw_alliance_match=True,
        raw_alliance_case_sensitive_mismatch=False,
        raw_name_display_exact=False,
        raw_name_normalized_match=False,
        name_normalized_similarity=0.6,
        raw_power_match=True,
        pre_core_safe=True,
    )
    assert skipped == 1
    assert len(kept) == 1
    assert kept[0].field == "alliance_tag"
    assert "budget_skip_core_safe_player_target" in reasons


def test_nonlocal_policy_skip_is_not_evidence_missing_when_core_safe():
    row = pd.Series({
        "alignment_context_gap": False,
        "valid_match": True,
        "alignment_guard_status": "row_alignment_observed",
        "character_verification_candidate": True,
        "character_reocr_status": "not_requested_policy_nonlocal",
        "verified_core_identity_match": True,
        "gold_core_blocker": False,
    })
    status, reason = _row_evidence_status(row, pd.DataFrame())
    assert status == "ROW_OK_POLICY_NONLOCAL"
    assert "nonlocal" in reason.lower()


def test_nonlocal_policy_skip_remains_review_when_core_blocked():
    row = pd.Series({
        "alignment_context_gap": False,
        "valid_match": True,
        "alignment_guard_status": "row_alignment_observed",
        "character_verification_candidate": True,
        "character_reocr_status": "not_requested_policy_nonlocal",
        "verified_core_identity_match": False,
        "gold_core_blocker": True,
    })
    status, reason = _row_evidence_status(row, pd.DataFrame())
    assert status == "ROW_POLICY_NONLOCAL_REVIEW"
    assert "review" in reason.lower()
