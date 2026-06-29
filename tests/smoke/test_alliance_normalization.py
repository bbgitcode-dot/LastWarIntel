from parser.alliance_normalization import build_alliance_vocabulary, normalize_alliance_tag


def test_alliance_tag_missing_middle_character_is_repaired():
    vocab = build_alliance_vocabulary(["PBC", "IVE", "PWW"])
    result = normalize_alliance_tag("PC", vocab)
    assert result.value == "PBC"
    assert result.match_type == "normalized"


def test_alliance_tag_missing_suffix_is_repaired():
    vocab = build_alliance_vocabulary(["PBC", "IVE", "PWW"])
    result = normalize_alliance_tag("IV", vocab)
    assert result.value == "IVE"


def test_alliance_tag_exact_match_stays_exact():
    vocab = build_alliance_vocabulary(["PBC", "IVE"])
    result = normalize_alliance_tag("[pbc]", vocab)
    assert result.value == "PBC"
    assert result.match_type == "exact"
