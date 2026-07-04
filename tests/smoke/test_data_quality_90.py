from parser.ranking import merge_rows_by_power
from parser.ranking_power_sanity_guard import PowerRecoveryCandidate, _pending_placeholder


def test_visible_rank_lock_beats_power_sort_for_sven_slot():
    rows = [
        {
            "rank": 10,
            "ocr_rank": 10,
            "player_name": "sven the vän",
            "name": "sven the vän",
            "alliance_tag": "SWSq",
            "power": 203_127_008,
            "source_file": "Screenshot_20260701-194413.png",
        },
        {
            "rank": 11,
            "ocr_rank": 11,
            "player_name": "umar712233",
            "name": "umar712233",
            "alliance_tag": "EWY",
            "power": 201_830_284,
            "source_file": "Screenshot_20260701-194413.png",
        },
        {
            "rank": 15,
            "ocr_rank": 15,
            "player_name": "Other",
            "name": "Other",
            "alliance_tag": "SWSq",
            "power": 200_312_700,
            "source_file": "Screenshot_20260701-194413.png",
        },
    ]

    merged = merge_rows_by_power(rows, limit=10, tolerance=0)

    assert [row["rank"] for row in merged] == [10, 11, 15]
    assert merged[0]["raw_player_name"] == "sven the vän"
    assert merged[0]["raw_alliance_tag"] == "SWSq"
    assert merged[0]["operational_rank"] == 10
    assert merged[0]["rank_slot_preserved"] is True


def test_pending_low_truncation_review_does_not_overwrite_observed_power_or_identity():
    row = {
        "rank": 10,
        "ocr_rank": 10,
        "player_name": "sven the vän",
        "name": "sven the vän",
        "alliance_tag": "SWSq",
        "power": 20_312_700,
        "hero_power": 20_312_700,
        "source_file": "Screenshot_20260701-194413.png",
    }
    candidates = [
        PowerRecoveryCandidate(200_312_700, 1.0418, ["insert_zero"], 0.68),
        PowerRecoveryCandidate(203_127_000, 1.0183, ["scale_x10_truncated_digit"], 0.92),
    ]

    pending = _pending_placeholder(row, ranking_type="total_hero_power", reason="power_recovery_candidates_ambiguous", candidates=candidates)

    assert pending["rank"] == 10
    assert pending["power"] == 20_312_700
    assert pending["hero_power"] == 20_312_700
    assert pending["power_sort_anchor"] == 200_312_700
    assert pending["raw_player_name"] == "sven the vän"
    assert pending["raw_alliance_tag"] == "SWSq"
    assert pending["observed_name"] == "sven the vän"
    assert pending["name"] == "PENDING REVIEW | sven the vän"


def test_quarantine_slot_keeps_following_ranks_from_collapsing():
    rows = [
        {"rank": 5, "ocr_rank": 5, "name": "PENDING REVIEW | [PAN]", "power": 22_709_655_122, "source_file": "s552.png"},
        {"rank": 6, "ocr_rank": 6, "name": "[BwD]", "power": 22_085_297_891, "source_file": "s552.png"},
        {"rank": 7, "ocr_rank": 7, "name": "[oAo]", "power": 20_477_544_820, "source_file": "s552.png"},
    ]

    merged = merge_rows_by_power(rows, limit=10, tolerance=0)

    assert [row["rank"] for row in merged] == [5, 6, 7]
    assert all(row["rank_slot_preserved"] is True for row in merged)
