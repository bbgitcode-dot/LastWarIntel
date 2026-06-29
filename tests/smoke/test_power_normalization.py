from parser.power_normalization import compare_power


def test_exact_power_match():
    result = compare_power(416693161, 416693161)
    assert result.match is True
    assert result.match_type == "exact"
    assert result.similarity == 1.0


def test_truncated_power_scale_x10_match():
    result = compare_power(239561010, 23956100)
    assert result.match is True
    assert result.match_type == "scale_x10_truncated_digit"
    assert result.recovered_actual == 239561000
    assert result.similarity > 0.999


def test_insert_zero_power_match():
    result = compare_power(250009089, 25009089)
    assert result.match is True
    assert result.match_type == "insert_zero"
    assert result.recovered_actual == 250009089
