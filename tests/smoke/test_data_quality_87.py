from main import parse_args
from parser.ranking_power_sanity_guard import PowerRecoveryCandidate, _pending_placeholder
from parser.ranking_guard import apply_ranking_guard


def test_development_mode_is_default_and_cache_requires_explicit_opt_in():
    args = parse_args([])
    assert args.mode == "development"
    assert args.ocr_cache is False
    assert args.no_ocr_cache is False


def test_ranking_type_quarantine_keeps_pending_slot_in_source_group():
    grouped = {
        (549, "alliance_power"): [
            {"name": "", "power": 1_000_000_000, "source_file": "a.png", "ocr_rank": 6},
        ]
    }
    guarded = apply_ranking_guard(grouped)
    assert (549, "alliance_power") in guarded
    assert guarded[(549, "alliance_power")][0]["pending_review"] is True
    assert guarded[(549, "alliance_power")][0]["rank_slot_preserved"] is True
    assert ("REVIEW", "ranking_guard_quarantine") in guarded


def test_power_pending_placeholder_preserves_observed_identity_and_candidate_anchor():
    row = {
        "name": "Sven the vän",
        "power": 20_312_700,
        "source_file": "s.png",
        "ocr_rank": 10,
        "player_name": "Sven the vän",
        "alliance_tag": "SWSq",
    }
    candidate = PowerRecoveryCandidate(203_127_000, 1.01, ["scale_x10_truncated_digit"], 0.92)
    pending = _pending_placeholder(row, ranking_type="total_hero_power", reason="ambiguous", candidates=[candidate])

    assert pending["pending_review"] is True
    assert pending["rank_slot_preserved"] is True
    assert pending["observed_name"] == "Sven the vän"
    assert pending["observed_alliance"] == "SWSq"
    assert pending["power_sort_anchor"] == 203_127_000
