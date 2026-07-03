from web.routes.reviews import _enrich_review_item
from services.command_center import _human_problem_statement


def test_review_detail_overlay_uses_row_inside_visible_window():
    item = _enrich_review_item({
        "ranking_type": "total_hero_power",
        "rank": 66,
        "visible_rank": 66,
        "raw_review_rank": 3,
        "screenshot_rank_window": {"start": 64, "end": 72, "count": 9},
        "target_name": "SUPER YASU",
        "target_alliance": "[TOS]",
        "target_power_selected": 236_773_679,
        "screenshot": "s.png",
    })
    assert item["display_rank"] == 66
    assert item["screenshot_rank_window_label"] == "64-72"
    assert item["target_name_display"] == "SUPER YASU"
    assert item["target_alliance_display"] == "[TOS]"
    assert item["target_power_display"] == "236.773.679"
    assert "Rank 66" in item["rank_highlight_label"]
    assert "top:29." in item["rank_highlight_style"]  # row 3, not rank 66


def test_problem_statement_names_target_and_visible_rank():
    review = {
        "server": 554,
        "ranking_type": "total_hero_power",
        "visible_rank": 66,
        "rank": 66,
        "raw_review_rank": 3,
        "target_name": "SUPER YASU",
        "target_alliance": "[TOS]",
        "screenshot_rank_window": {"start": 64, "end": 72, "count": 9},
        "reason": "ranking_guard_quarantine",
    }
    trace = {
        "status": "ambiguous",
        "best_candidate": 167_730_565,
        "second_candidate": 159_730_565,
        "candidates": [
            {"value": 167_730_565, "score": 0.7, "reasons": []},
            {"value": 159_730_565, "score": 0.6, "reasons": []},
        ],
    }
    statement = _human_problem_statement("REV-003", review, trace)
    assert "SUPER YASU" in statement
    assert "[TOS]" in statement
    assert "Operational Rank 66" in statement
    assert "Screenshot window 64-72" in statement
