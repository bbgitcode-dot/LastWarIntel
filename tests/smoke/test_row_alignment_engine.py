from parser.ranking import parse_ranking_rows


def _box(x1, y1, x2, y2):
    return [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]


def test_row_alignment_prevents_shift_when_rank_is_vertically_offset():
    ocr = [
        (_box(20, 100, 40, 122), "4", 0.99),
        (_box(80, 106, 160, 128), "[IVE]", 0.96),
        (_box(170, 106, 300, 128), "LOVE BIEN", 0.95),
        (_box(520, 108, 650, 130), "296,706,059", 0.99),
        # Next row. The rank is a little high, a common OCR layout artifact.
        (_box(20, 146, 40, 168), "5", 0.99),
        (_box(80, 160, 160, 182), "[PBC]", 0.96),
        (_box(170, 160, 340, 182), "Wowamonkey 브로", 0.95),
        (_box(520, 162, 650, 184), "292,896,181", 0.99),
    ]

    rows = parse_ranking_rows(ocr)

    assert len(rows) == 2
    assert rows[0]["ocr_rank"] == 4
    assert "LOVE BIEN" in rows[0]["name"]
    assert rows[0]["power"] == 296_706_059
    assert rows[1]["ocr_rank"] == 5
    assert "Wowamonkey" in rows[1]["name"]
    assert rows[1]["power"] == 292_896_181


def test_row_alignment_uses_power_anchor_and_reports_missing_rank():
    ocr = [
        (_box(80, 106, 160, 128), "[PBC]", 0.96),
        (_box(170, 106, 300, 128), "Fallen Grace", 0.95),
        (_box(520, 108, 650, 130), "232,494,296", 0.99),
    ]

    rows = parse_ranking_rows(ocr)

    assert len(rows) == 1
    assert rows[0]["name"] == "[PBC] Fallen Grace"
    assert rows[0]["power"] == 232_494_296
    assert "missing_rank_anchor" in rows[0]["alignment_warning"]
