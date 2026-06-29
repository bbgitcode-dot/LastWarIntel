import pandas as pd

from parser.sequence_alignment import find_best_sequence_candidate


def _name_similarity(a: str, b: str) -> float:
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a.upper(), b.upper()).ratio()


def test_sequence_alignment_prefers_recovered_power_with_name_evidence():
    candidates = pd.DataFrame([
        {"rank": 21, "power": 236436076, "ocr_name": "Zacharys", "alliance": "PBC"},
        {"rank": 39, "power": 25009089, "ocr_name": "Kg Thunder", "alliance": "IVE"},
    ])
    row, method, candidate = find_best_sequence_candidate(
        expected_rank=21,
        expected_power=250009089,
        expected_name="K9 Thunder",
        expected_alliance="IVE",
        candidates=candidates,
        normalize_name=lambda value: str(value or ""),
        normalize_tag=lambda value: str(value or "").upper(),
        name_similarity=_name_similarity,
        alliance_match=lambda expected, actual: expected == actual,
    )
    assert row is not None
    assert row["ocr_name"] == "Kg Thunder"
    assert method.startswith("sequence_")
    assert candidate.power.match is True


def test_sequence_alignment_rejects_recovered_power_without_name_evidence():
    candidates = pd.DataFrame([
        {"rank": 38, "power": 23956100, "ocr_name": "M0 X HUNI", "alliance": "IVE"},
    ])
    row, method, candidate = find_best_sequence_candidate(
        expected_rank=38,
        expected_power=230761273,
        expected_name="WorkOut Durumi",
        expected_alliance="IVE",
        candidates=candidates,
        normalize_name=lambda value: str(value or ""),
        normalize_tag=lambda value: str(value or "").upper(),
        name_similarity=_name_similarity,
        alliance_match=lambda expected, actual: expected == actual,
    )
    assert row is None
    assert method == "missing"
    assert candidate is None
