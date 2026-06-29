from parser.server import detect_server_consensus_from_ocr


def box():
    return [(0, 0), (1, 0), (1, 1), (0, 1)]


def test_server_consensus_accepts_three_equal_warzone_hits():
    result = detect_server_consensus_from_ocr([
        (box(), "Warzone #549", 0.9),
        (box(), "Warzone #549", 0.9),
        (box(), "Warzone #549", 0.9),
    ])
    assert result.server == 549
    assert result.warning is None
    assert result.confidence == 1.0


def test_server_consensus_rejects_insufficient_evidence():
    result = detect_server_consensus_from_ocr([
        (box(), "Warzone #549", 0.9),
        (box(), "Warzone #549", 0.9),
    ])
    assert result.server is None
    assert result.warning.startswith("server_consensus_below_threshold")
