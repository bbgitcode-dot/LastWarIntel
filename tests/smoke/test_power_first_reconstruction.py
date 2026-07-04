from parser.ranking import merge_rows_by_power


def test_visible_rank_is_authoritative_when_ocr_rank_shifted():
    rows = [
        {"name": "A", "power": 300, "ocr_rank": 1},
        {"name": "B", "power": 200, "ocr_rank": 7},
        {"name": "C", "power": 100, "ocr_rank": 8},
    ]

    merged = merge_rows_by_power(rows, limit=3, tolerance=0)

    assert [row["rank"] for row in merged] == [1, 7, 8]
    assert [row["computed_rank"] for row in merged] == [1, 2, 3]
    assert merged[1]["ocr_rank"] == 7
    assert merged[1]["rank_slot_preserved"] is True
