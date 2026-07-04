from parser.ranking import merge_rows_by_power


def test_merge_preserves_ocr_rank_and_detects_gap():
    rows = [
        {"name": "A", "power": 300, "ocr_rank": 79},
        {"name": "B", "power": 200, "ocr_rank": 81},
    ]
    merged = merge_rows_by_power(rows, limit=10, tolerance=0.0)

    assert merged[0]["rank"] == 79
    assert merged[0]["computed_rank"] == 1
    assert merged[0]["rank_slot_preserved"] is True
    assert merged[1]["rank"] == 81
    assert "possible_missing_rank_before:80" in merged[1]["rank_warning"]


def test_merge_does_not_warn_every_row_when_ocr_rank_missing():
    rows = [{"name": "A", "power": 300}]
    merged = merge_rows_by_power(rows, limit=10, tolerance=0.0)
    assert merged[0]["rank"] == 1
    assert merged[0]["rank_warning"] == ""
