from parser.ranking import parse_ranking_rows
from parser.player_ranking import split_alliance_tag_and_player_name


def _box(x1, y1, x2, y2):
    return [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]


def test_column_reconstruction_ignores_badge_noise_before_alliance():
    ocr = [
        (_box(20, 100, 40, 122), "4", 0.99),
        (_box(70, 106, 130, 128), "0咀#5", 0.70),
        (_box(140, 106, 230, 128), "[IVE]", 0.96),
        (_box(240, 106, 360, 128), "LOVE BIEN", 0.95),
        (_box(520, 108, 650, 130), "296,706,059", 0.99),
    ]

    rows = parse_ranking_rows(ocr)

    assert len(rows) == 1
    assert rows[0]["name"] == "[IVE] LOVE BIEN"
    assert "tokens_before_alliance_column_ignored" in rows[0]["column_corrections"]


def test_column_reconstruction_repairs_missing_open_alliance_bracket():
    ocr = [
        (_box(20, 100, 40, 122), "3", 0.99),
        (_box(70, 106, 130, 128), "0}#E", 0.70),
        (_box(140, 106, 360, 128), "IPbC] Monkopeace * 号卫", 0.93),
        (_box(520, 108, 650, 130), "317,058,104", 0.99),
    ]

    rows = parse_ranking_rows(ocr)
    tag, name = split_alliance_tag_and_player_name(rows[0]["name"])

    assert tag == "PbC"
    assert "Monkopeace" in name
    assert "missing_open_alliance_bracket_repaired" in rows[0]["column_corrections"]


def test_column_reconstruction_keeps_name_without_alliance_when_readable():
    ocr = [
        (_box(20, 100, 40, 122), "37", 0.99),
        (_box(120, 106, 260, 128), "달서구민", 0.93),
        (_box(520, 108, 650, 130), "231,047,233", 0.99),
    ]

    rows = parse_ranking_rows(ocr)

    assert rows[0]["name"] == "달서구민"
    assert "alliance_column_not_detected" in rows[0]["alignment_warning"]
