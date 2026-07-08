from parser.targeted_character_reocr import CharacterVerificationEvidence, ReOcrTarget
from ground_truth_validator import _target_cache_key, _clone_cached_reocr_evidence, _cacheable_reocr_evidence


def test_reocr_evidence_cache_key_is_exact_target_and_text_pair():
    target = ReOcrTarget(field="alliance_tag", position=1, expected="b", observed="B", reason="case_sensitive_tag_difference")
    key_a = _target_cache_key(target, expected_text="PbC", observed_text="PBC")
    key_b = _target_cache_key(target, expected_text="PbC", observed_text="PC")
    assert key_a != key_b
    assert key_a[0] == "alliance_tag"
    assert key_a[2] == "b"


def test_cacheable_reocr_evidence_accepts_only_decisive_glyph_outcomes():
    ok = CharacterVerificationEvidence(
        field="player_name", position=0, expected="D", observed="O", screenshot="a.png", row_slot=0,
        crop_box=(0, 0, 1, 1), status="verified_expected", selected="D", confidence=1.0,
    )
    bad = CharacterVerificationEvidence(
        field="player_name", position=0, expected="D", observed="O", screenshot="a.png", row_slot=0,
        crop_box=(0, 0, 1, 1), status="unresolved",
    )
    assert _cacheable_reocr_evidence(ok) is True
    assert _cacheable_reocr_evidence(bad) is False


def test_cached_evidence_clone_marks_cache_hit_without_reusing_crop():
    target = ReOcrTarget(field="player_name", position=0, expected="D", observed="O", reason="ocr_confusable_character_difference")
    source = CharacterVerificationEvidence(
        field="player_name", position=0, expected="D", observed="O", screenshot="a.png", row_slot=1,
        crop_box=(10, 20, 30, 40), status="verified_expected", selected="D", confidence=1.0,
    )
    clone = _clone_cached_reocr_evidence(
        source,
        target=target,
        screenshot="b.png",
        row_slot=2,
        expected_text="Disneys Mushu",
        observed_text="Oisneys Mushu",
    )
    assert clone.status == "verified_expected"
    assert clone.reason == "evidence_cache_hit"
    assert clone.crop_strategy == "snapshot_evidence_cache"
    assert clone.crop_box is None
    assert clone.screenshot == "b.png"
    assert clone.row_slot == 2
