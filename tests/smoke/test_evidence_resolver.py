import pandas as pd

from parser.evidence_resolver import find_same_server_evidence_candidate


def _norm_name(value):
    return str(value or '').strip()


def _norm_tag(value):
    return str(value or '').strip().upper()


def _sim(expected, actual):
    return 1.0 if str(expected).casefold() == str(actual).casefold() else 0.0


def _tag_match(expected, actual):
    return _norm_tag(expected) == _norm_tag(actual)


def test_evidence_resolver_accepts_unique_exact_power_with_weak_identity():
    rows = pd.DataFrame([
        {"server": 551, "rank": 7, "power": 289587066, "ocr_name": "Trapppppy", "alliance": "PBC"},
        {"server": 551, "rank": 8, "power": 286697731, "ocr_name": "UNKNOWN", "alliance": ""},
        {"server": 551, "rank": 9, "power": 272378748, "ocr_name": "XZed", "alliance": "PC"},
    ])

    match, method, candidate = find_same_server_evidence_candidate(
        expected_rank=8,
        expected_power=286697731,
        expected_name="GD VIP",
        expected_alliance="IVE",
        candidates=rows,
        normalize_name=_norm_name,
        normalize_tag=_norm_tag,
        name_similarity=_sim,
        alliance_match=_tag_match,
    )

    assert match is not None
    assert method == "gap_same_server_exact_power"
    assert candidate is not None
    assert candidate.evidence == "unique_exact_power"


def test_evidence_resolver_rejects_duplicate_exact_power():
    rows = pd.DataFrame([
        {"server": 551, "rank": 8, "power": 286697731, "ocr_name": "UNKNOWN", "alliance": ""},
        {"server": 551, "rank": 88, "power": 286697731, "ocr_name": "Other", "alliance": ""},
    ])

    match, method, candidate = find_same_server_evidence_candidate(
        expected_rank=8,
        expected_power=286697731,
        expected_name="GD VIP",
        expected_alliance="IVE",
        candidates=rows,
        normalize_name=_norm_name,
        normalize_tag=_norm_tag,
        name_similarity=_sim,
        alliance_match=_tag_match,
    )

    assert match is None
    assert method == "missing"
    assert candidate is None
