from parser.ranking import merge_rows_by_power


def test_unranked_rows_do_not_displace_visible_slots_in_ranked_context():
    rows = [
        {"ocr_rank": 4, "name": "[3DNG] top visible", "power": 27_991_893_823, "source_file": "top.png"},
        {"ocr_rank": 5, "name": "[nLs] second visible", "power": 23_873_369_613, "source_file": "top.png"},
        {"name": "[709] cats ai later window", "power": 1_781_412_101, "source_file": "later.png"},
    ]

    merged = merge_rows_by_power(rows, limit=10, tolerance=0)

    locked = [row for row in merged if row.get("final_rank") is not None]
    diagnostics = [row for row in merged if row.get("rank_context_status") == "quarantine_missing_visible_rank"]

    assert [row["rank"] for row in locked] == [4, 5]
    assert diagnostics
    assert diagnostics[0]["rank"] is None
    assert "not_promoted_to_operational_truth" in diagnostics[0]["rank_warning"]


def test_duplicate_visible_rank_cross_window_conflict_keeps_slot_and_diagnostics():
    rows = [
        {"ocr_rank": 1, "name": "[EVIL] progress", "power": 30_827_950_857, "source_file": "555_top.png"},
        {"ocr_rank": 1, "name": "[GOPP] different later row", "power": 24_606_329_562, "source_file": "555_later.png"},
        {"ocr_rank": 2, "name": "[KOS] Knights Of Shadow", "power": 25_430_833_828, "source_file": "555_top.png"},
    ]

    merged = merge_rows_by_power(rows, limit=10, tolerance=0)

    rank1 = [row for row in merged if row.get("rank") == 1][0]
    conflict_diag = [row for row in merged if row.get("rank_context_status") == "quarantine_duplicate_visible_rank_conflict"]

    assert rank1["name"] == "[EVIL] progress"
    assert "duplicate_visible_rank_slot_cross_window_conflict" in rank1["rank_warning"]
    assert conflict_diag
    assert conflict_diag[0]["final_rank"] is None
