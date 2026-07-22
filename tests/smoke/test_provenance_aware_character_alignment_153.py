import json
import pandas as pd

from ground_truth_validator import (
    _apply_display_reconstruction,
    _build_gold_core_character_evidence_map,
    _build_position_evidence_acquisition_bridge,
    _provenance_aware_character_alignment,
)


def _row(expected_name="Drpeek", ocr_name="Ieek", **overrides):
    row = {
        "server": 551,
        "rank": 11,
        "expected_name": expected_name,
        "ocr_name": ocr_name,
        "ocr_source_file": "lastwar_export.xlsx",
        "ocr_sheet": "THP",
        "screenshot": "thp_03.png",
        "row_slot": 4,
        "gold_core_blocker_after_elimination": True,
        "promotion_guard_primary_blocker": "name_exact",
        "character_reocr_evidence": "[]",
        "read_only_reocr_evidence": "[]",
    }
    row.update(overrides)
    return row


def test_alignment_emits_explicit_edit_operations_and_preserves_sources():
    source = [{"position": i, "character": ch, "source_chain_status": "ROW_OCR_SOURCE_BOUND"} for i, ch in enumerate("Ieek")]
    aligned, inserts = _provenance_aware_character_alignment("Drpeek", "Ieek", source)
    operations = [item["alignment_operation"] for item in aligned]
    assert len(aligned) == len("Drpeek")
    assert "DELETE" in operations or "SUBSTITUTE" in operations
    assert all(item["gold_authoritative"] is False for item in aligned)
    assert all(item["alignment_operation"] == "INSERT" for item in inserts)


def test_unknown_is_never_aligned_as_character_evidence():
    source = [{"position": i, "character": ch, "source_chain_status": "ROW_OCR_SOURCE_BOUND"} for i, ch in enumerate("UNKNOWN")]
    aligned, inserts = _provenance_aware_character_alignment("시로시로 Mio", "UNKNOWN", source)
    assert not inserts
    assert aligned
    assert {item["alignment_operation"] for item in aligned} == {"AMBIGUOUS"}
    assert {item["alignment_reason"] for item in aligned} == {"unknown_base_not_character_evidence"}


def test_non_space_glyph_cannot_prove_separator():
    source = [{"position": 0, "character": "X", "source_chain_status": "ROW_OCR_SOURCE_BOUND"}]
    aligned, _ = _provenance_aware_character_alignment("A B", "AXB", [{"position": i, "character": ch, "source_chain_status": "ROW_OCR_SOURCE_BOUND"} for i, ch in enumerate("AXB")])
    assert aligned[1]["alignment_operation"] == "AMBIGUOUS"
    assert aligned[1]["alignment_reason"] == "non_separator_glyph_cannot_prove_separator"


def test_exact_alignment_can_bridge_without_gold_promotion():
    detail = _apply_display_reconstruction(pd.DataFrame([_row(expected_name="Drpeek", ocr_name="Drpeek")]))
    _, positions, _ = _build_gold_core_character_evidence_map(detail)
    _, bridge, _, _ = _build_position_evidence_acquisition_bridge(detail, positions)
    first = bridge[bridge["position"] == 0].iloc[0]
    assert first["binding_status"] == "BRIDGED_POSITION_EVIDENCE"
    assert first["binding_method"] == "provenance_aware_alignment"
    assert first["alignment_operation"] == "MATCH"
    assert first["display_source_gold_authoritative"] == False
    assert first["operational_truth_modified"] == False


def test_substitution_is_counterevidence_not_safe_binding():
    detail = _apply_display_reconstruction(pd.DataFrame([_row(expected_name="A", ocr_name="B")]))
    _, positions, _ = _build_gold_core_character_evidence_map(detail)
    _, bridge, _, _ = _build_position_evidence_acquisition_bridge(detail, positions)
    first = bridge.iloc[0]
    assert first["alignment_operation"] == "SUBSTITUTE"
    assert first["binding_status"] == "CONFLICTING_POSITION_EVIDENCE"
    assert first["binding_reason"] == "source_bound_character_differs_from_target_position"


def test_display_report_contains_alignment_trace():
    detail = _apply_display_reconstruction(pd.DataFrame([_row()]))
    row = detail.iloc[0]
    trace = json.loads(row["display_character_alignment"])
    assert trace
    assert "alignment_operation" in trace[0]
    assert row["display_alignment_matches"] >= 1
