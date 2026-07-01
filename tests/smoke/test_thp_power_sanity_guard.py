from parser.thp_sanity_guard import apply_thp_power_sanity_guard


def _row(power, source):
    return {"name": f"[TAG] player {power}", "power": power, "source_file": source}


def test_late_scroll_thp_outlier_is_quarantined():
    grouped = {
        (552, "total_hero_power"): [
            _row(403_000_000, "001.png"),
            _row(322_000_000, "001.png"),
            _row(310_000_000, "001.png"),
            _row(294_000_000, "001.png"),
            _row(798_000_000, "002.png"),
            _row(200_000_000, "002.png"),
            _row(199_000_000, "002.png"),
            _row(198_000_000, "002.png"),
            _row(197_000_000, "002.png"),
        ]
    }

    result = apply_thp_power_sanity_guard(grouped)

    assert len(result[(552, "total_hero_power")]) == 8
    quarantine = result[("REVIEW", "ranking_guard_quarantine")]
    assert len(quarantine) == 1
    assert quarantine[0]["power"] == 798_000_000
    assert quarantine[0]["quarantine_reason"] == "thp_power_sanity_outlier"


def test_first_thp_screenshot_can_contain_real_whales():
    grouped = {
        (552, "total_hero_power"): [
            _row(827_000_000, "001.png"),
            _row(821_000_000, "001.png"),
            _row(403_000_000, "001.png"),
            _row(322_000_000, "001.png"),
            _row(310_000_000, "001.png"),
        ]
    }

    result = apply_thp_power_sanity_guard(grouped)

    assert ("REVIEW", "ranking_guard_quarantine") not in result
    assert len(result[(552, "total_hero_power")]) == 5


def test_normal_scroll_overlap_is_allowed():
    grouped = {
        (552, "total_hero_power"): [
            _row(403_000_000, "001.png"),
            _row(322_000_000, "001.png"),
            _row(310_000_000, "001.png"),
            _row(294_000_000, "001.png"),
            _row(275_000_000, "002.png"),
            _row(272_000_000, "002.png"),
            _row(219_000_000, "002.png"),
            _row(218_000_000, "002.png"),
            _row(217_000_000, "002.png"),
        ]
    }

    result = apply_thp_power_sanity_guard(grouped)

    assert ("REVIEW", "ranking_guard_quarantine") not in result
    assert len(result[(552, "total_hero_power")]) == 9
