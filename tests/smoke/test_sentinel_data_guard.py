from parser.data_guard import resolve_server_assignment
from parser.server import ServerDetection


def _ocr(text):
    return [([[0, 0], [1, 0], [1, 1], [0, 1]], text, 0.99)]


def test_row_warzone_majority_overrides_wrong_metadata_server():
    metadata = ServerDetection(
        server=552,
        confidence=1.0,
        source="ocr_consensus",
        detections=[552, 552, 552],
        warning=None,
    )
    row_ocr = _ocr("Warzone #551") + _ocr("Warzone #551") + _ocr("Warzone #551") + _ocr("Warzone #551")

    decision = resolve_server_assignment(metadata, row_ocr)

    assert decision.server == 551
    assert decision.conflict is True
    assert decision.source == "data_guard:row_warzone_override"
    assert "server_assignment_conflict" in (decision.warning or "")


def test_metadata_is_kept_when_row_evidence_is_weak():
    metadata = ServerDetection(
        server=551,
        confidence=1.0,
        source="ocr_consensus",
        detections=[551, 551, 551],
        warning=None,
    )
    row_ocr = _ocr("Warzone #552")

    decision = resolve_server_assignment(metadata, row_ocr)

    assert decision.server == 551
    assert decision.conflict is False
    assert decision.source == "ocr_consensus"

from parser.data_guard import reconcile_server_assignments_by_content


def _row(rank, tag, power, *, source='s.png', confidence=0.6):
    return {
        'rank': rank,
        'alliance_tag': tag,
        'name': f'[{tag}] Player{rank}',
        'power': power,
        'source_file': source,
        'server_confidence': confidence,
        'server_warning': None,
        'data_guard_conflict': False,
    }


def test_content_guard_quarantines_small_low_confidence_block_without_filename_timestamps():
    target_rows = [_row(i, 'IVE' if i % 2 else 'PWW', 300_000_000 - i * 1_000_000, source=f'random_{i}.png', confidence=1.0) for i in range(1, 101)]
    suspect_rows = [
        _row(1, 'IVE', 248_000_000, source='IMG_0001.jpg', confidence=0.6),
        _row(2, 'PWW', 242_000_000, source='totally_random_name.jpg', confidence=0.6),
        _row(3, 'IVE', 201_000_000, source='upload.png', confidence=0.6),
    ]
    grouped = {
        (551, 'total_hero_power'): target_rows,
        (552, 'total_hero_power'): suspect_rows,
    }

    resolved = reconcile_server_assignments_by_content(grouped, min_score=0.70)

    assert (552, 'total_hero_power') not in resolved
    assert len(resolved[(551, 'total_hero_power')]) == 100
    assert ('REVIEW', 'data_guard_quarantine') in resolved
    assert len(resolved[('REVIEW', 'data_guard_quarantine')]) == 3
    assert all(row['data_guard_conflict'] for row in suspect_rows)
    assert all(row['server_source'] == 'data_guard:quarantine' for row in suspect_rows)
    assert all(row['quarantine_reason'] == 'server_assignment_conflict' for row in suspect_rows)


def test_content_guard_does_not_reassign_unrelated_small_server_block():
    target_rows = [_row(i, 'IVE', 300_000_000 - i * 1_000_000, confidence=1.0) for i in range(1, 61)]
    suspect_rows = [
        _row(1, 'WARF', 190_000_000, confidence=0.6),
        _row(2, 'LSC', 180_000_000, confidence=0.6),
        _row(3, 'WARF', 170_000_000, confidence=0.6),
    ]
    grouped = {
        (551, 'total_hero_power'): target_rows,
        (552, 'total_hero_power'): suspect_rows,
    }

    resolved = reconcile_server_assignments_by_content(grouped, min_score=0.70)

    assert (552, 'total_hero_power') in resolved
    assert len(resolved[(551, 'total_hero_power')]) == 60
    assert len(resolved[(552, 'total_hero_power')]) == 3
