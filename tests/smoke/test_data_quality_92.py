from parser.ranking import merge_rows_by_power


def test_full_scope_missing_visible_ranks_are_inferred_from_power_order():
    rows = [
        {"name": f"Player {idx}", "power": 300_000_000 - idx, "source_file": f"window_{idx // 7}.png"}
        for idx in range(25)
    ]

    merged = merge_rows_by_power(rows, limit=25, tolerance=0)

    assert [row["rank"] for row in merged[:5]] == [1, 2, 3, 4, 5]
    assert all(row["rank_context_status"] == "inferred_power_order_rank_missing_visible_rank" for row in merged)
    assert all(row["final_rank"] == row["rank"] for row in merged)


def test_full_scope_bad_ocr_rank_is_repaired_but_preserved_as_visible_evidence():
    rows = [
        {"name": "Joncollinszl", "alliance_tag": "PBC", "power": 416_693_161, "source_file": "551_top_1.png"},
        {"name": "MEITTi", "alliance_tag": "IVE", "power": 320_306_010, "ocr_rank": 800, "source_file": "551_top_1.png"},
        {"name": "Monkopeace", "alliance_tag": "PBC", "power": 317_058_104, "ocr_rank": 300, "source_file": "551_top_1.png"},
    ]
    # Add enough rows/windows to activate full-scope inference, matching the 551
    # benchmark pattern where the rank column is weak but the power ordering is
    # reliable across screenshot windows.
    for idx in range(3, 25):
        rows.append({"name": f"P{idx}", "power": 300_000_000 - idx, "source_file": f"551_win_{idx // 7}.png"})

    merged = merge_rows_by_power(rows, limit=25, tolerance=0)

    assert merged[1]["rank"] == 2
    assert merged[1]["visible_rank"] == 800
    assert merged[1]["rank_context_status"] == "rank_scope_repaired_by_power_order"
    assert "rank_scope_violation_repaired_by_power_order" in merged[1]["rank_warning"]
    assert merged[2]["rank"] == 3
    assert merged[2]["visible_rank"] == 300


def test_partial_window_visible_ranks_remain_authoritative():
    rows = [
        {"name": "Window Rank 79", "power": 300, "ocr_rank": 79, "source_file": "partial.png"},
        {"name": "Window Rank 81", "power": 200, "ocr_rank": 81, "source_file": "partial.png"},
    ]

    merged = merge_rows_by_power(rows, limit=100, tolerance=0)

    assert [row["rank"] for row in merged] == [79, 81]
    assert "possible_missing_rank_before:80" in merged[1]["rank_warning"]
