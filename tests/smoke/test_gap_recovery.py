import pandas as pd

from parser.gap_recovery import annotate_gap_recovery


def test_gap_recovery_marks_bounded_bad_rank_block():
    detail = pd.DataFrame([
        {"server": 551, "rank": 20, "match_method": "server_power", "bad_match": False, "power_match": True, "alliance_match": True, "name_normalized_match": True},
        {"server": 551, "rank": 21, "match_method": "blocked_rank_fallback", "bad_match": False, "power_match": False, "alliance_match": False, "name_normalized_match": False},
        {"server": 551, "rank": 22, "match_method": "blocked_rank_fallback", "bad_match": False, "power_match": False, "alliance_match": False, "name_normalized_match": False},
        {"server": 551, "rank": 23, "match_method": "server_power", "bad_match": False, "power_match": True, "alliance_match": True, "name_normalized_match": True},
    ])

    annotated, metrics = annotate_gap_recovery(detail)

    assert metrics["gap_blocks"] == 1
    assert metrics["gap_rows"] == 2
    assert metrics["recoverable_gap_blocks"] == 1
    assert metrics["recoverable_gap_rows"] == 2
    assert metrics["blocked_rank_fallbacks"] == 2
    gap_rows = annotated[annotated["gap_status"] == "blocked_rank_fallback"]
    assert set(gap_rows["gap_previous_anchor_rank"]) == {20}
    assert set(gap_rows["gap_next_anchor_rank"]) == {23}
    assert gap_rows["gap_recoverable"].all()
