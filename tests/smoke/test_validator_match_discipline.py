import pandas as pd

from ground_truth_validator import _find_match
from parser.alliance_normalization import build_alliance_vocabulary


def test_rank_fallback_rejects_clear_power_and_name_contradiction():
    gt = pd.Series({
        "server": 551,
        "rank": 22,
        "power": 248671604,
        "true_name": "YUNS",
        "alliance": "IVE",
    })
    ocr = pd.DataFrame([
        {
            "server": 551,
            "rank": 22,
            "power": 232494296,
            "ocr_name": "Fallen Grace",
            "alliance": "PBC",
        }
    ])
    vocab = build_alliance_vocabulary(["IVE", "PBC"])

    match, method, candidate = _find_match(gt, ocr, vocab)

    assert match is not None
    assert method == "blocked_rank_fallback"
    assert candidate is None


def test_rank_fallback_allows_useful_identity_evidence():
    gt = pd.Series({
        "server": 551,
        "rank": 11,
        "power": 271156279,
        "true_name": "Drpeek",
        "alliance": "PBC",
    })
    ocr = pd.DataFrame([
        {
            "server": 551,
            "rank": 11,
            "power": 271156279,
            "ocr_name": "Ieek",
            "alliance": "PBC",
        }
    ])
    vocab = build_alliance_vocabulary(["PBC"])

    match, method, candidate = _find_match(gt, ocr, vocab)

    assert match is not None
    assert method == "server_power" or method == "server_rank"
