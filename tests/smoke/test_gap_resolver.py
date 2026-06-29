import pandas as pd

from ground_truth_validator import _find_match
from parser.alliance_normalization import build_alliance_vocabulary
from parser.gap_resolver import find_cross_server_gap_candidate


def _name_similarity(a: str, b: str) -> float:
    from difflib import SequenceMatcher
    return SequenceMatcher(None, str(a).upper(), str(b).upper()).ratio()


def test_gap_resolver_pulls_wrong_server_row_with_strong_evidence():
    candidates = pd.DataFrame([
        {"server": 551, "rank": 22, "power": 232494296, "ocr_name": "Fallen Grace", "alliance": "PBC"},
        {"server": 552, "rank": 1, "power": 248671604, "ocr_name": "X YUNS", "alliance": "IVE"},
    ])

    row, method, candidate = find_cross_server_gap_candidate(
        expected_server=551,
        expected_rank=22,
        expected_power=248671604,
        expected_name="YUNS",
        expected_alliance="IVE",
        all_candidates=candidates,
        normalize_name=lambda value: str(value or ""),
        normalize_tag=lambda value: str(value or "").upper(),
        name_similarity=_name_similarity,
        alliance_match=lambda expected, actual: expected == actual,
    )

    assert row is not None
    assert row["server"] == 552
    assert method == "gap_cross_server_exact"
    assert candidate.score >= 0.82


def test_find_match_uses_gap_resolver_before_bad_rank_fallback():
    gt = pd.Series({
        "server": 551,
        "rank": 22,
        "power": 248671604,
        "true_name": "윤쓰윤쓰 X YUNS",
        "alliance": "IVE",
    })
    ocr = pd.DataFrame([
        {"server": 551, "rank": 22, "power": 232494296, "ocr_name": "Fallen Grace", "alliance": "PBC"},
        {"server": 552, "rank": 1, "power": 248671604, "ocr_name": "忌丛昱丛 X YUNS", "alliance": "IVE"},
    ])
    vocab = build_alliance_vocabulary(["IVE", "PBC"])

    match, method, candidate = _find_match(gt, ocr, vocab)

    assert match is not None
    assert method == "gap_cross_server_exact"
    assert int(match["server"]) == 552
    assert candidate is not None
