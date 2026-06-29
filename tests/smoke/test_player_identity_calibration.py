from parser.player_identity_quality import parse_player_identity_quality


def test_prefix_before_tag_is_correction_not_review():
    result = parse_player_identity_quality("FKGzzs [Warf] GoldCradle", base_confidence=0.72)
    assert result.alliance_tag == "Warf"
    assert result.player_name == "GoldCradle"
    assert result.status == "VALID"
    assert "prefix_before_alliance_tag_ignored" in result.corrections


def test_cjk_player_name_can_be_valid():
    result = parse_player_identity_quality("[o5s] けん41", base_confidence=0.70)
    assert result.alliance_tag == "o5s"
    assert result.player_name == "けん41"
    assert result.status == "VALID"


def test_unusable_name_goes_to_review():
    result = parse_player_identity_quality("[]", base_confidence=0.9)
    assert result.player_name == "UNKNOWN"
    assert result.status == "REVIEW"
