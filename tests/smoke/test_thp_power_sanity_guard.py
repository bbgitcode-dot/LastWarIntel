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


def test_thp_source_shape_blocks_late_scroll_digit_explosion_cluster():
    grouped = {
        (553, "total_hero_power"): [
            {
                "rank": 1,
                "computed_rank": 1,
                "ocr_rank": 5,
                "rank_warning": "ocr_rank_differs_from_power_rank:5!=1",
                "alliance_tag": "LAFA",
                "player_name": "chris711",
                "power": 764_292_586,
                "source_file": "tail.png",
            },
            {
                "rank": 2,
                "computed_rank": 2,
                "ocr_rank": 5,
                "rank_warning": "ocr_rank_differs_from_power_rank:5!=2",
                "alliance_tag": "LAFA",
                "player_name": "Pel Cowboy from Hell",
                "power": 764_007_632,
                "source_file": "tail.png",
            },
            {
                "rank": 3,
                "computed_rank": 3,
                "ocr_rank": 5,
                "rank_warning": "ocr_rank_differs_from_power_rank:5!=3",
                "alliance_tag": "SWSQ",
                "player_name": "st34km4n",
                "power": 763_106_065,
                "source_file": "tail.png",
            },
            {
                "rank": 4,
                "computed_rank": 4,
                "ocr_rank": 5,
                "rank_warning": "ocr_rank_differs_from_power_rank:5!=4",
                "alliance_tag": "SWSQ",
                "player_name": "Crank40",
                "power": 762_831_270,
                "source_file": "tail.png",
            },
            {
                "rank": 81,
                "computed_rank": 81,
                "ocr_rank": 5,
                "alliance_tag": "SWSQ",
                "player_name": "Bubellee",
                "power": 164_288_799,
                "source_file": "tail.png",
            },
            {
                "rank": 82,
                "computed_rank": 82,
                "alliance_tag": "SBRO",
                "player_name": "StealthNinja",
                "power": 163_645_571,
                "source_file": "tail.png",
            },
            {
                "rank": 83,
                "computed_rank": 83,
                "alliance_tag": "IXN",
                "player_name": "khs",
                "power": 163_475_086,
                "source_file": "tail.png",
            },
            {
                "rank": 84,
                "computed_rank": 84,
                "alliance_tag": "LAFA",
                "player_name": "Jupp2511",
                "power": 163_193_157,
                "source_file": "tail.png",
            },
        ]
    }

    result = apply_thp_power_sanity_guard(grouped)

    exported = result[(553, "total_hero_power")]
    quarantine = result[("REVIEW", "ranking_guard_quarantine")]
    assert [row["player_name"] for row in exported] == ["Bubellee", "StealthNinja", "khs", "Jupp2511"]
    assert {row["player_name"] for row in quarantine} == {
        "chris711",
        "Pel Cowboy from Hell",
        "st34km4n",
        "Crank40",
    }
    assert all("source_shape_digit_explosion" in row["ranking_guard_reason"] for row in quarantine)
