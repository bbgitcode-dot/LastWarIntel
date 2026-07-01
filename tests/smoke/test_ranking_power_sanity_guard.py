from parser.ranking_power_sanity_guard import apply_ranking_power_sanity_guard


def _row(power, source, rank=None, name=None):
    row = {"name": name or f"[TAG] item {power}", "power": power, "source_file": source}
    if rank is not None:
        row["ocr_rank"] = rank
        row["rank"] = rank
    return row


def test_alliance_power_local_outlier_is_quarantined_before_power_sort():
    grouped = {
        (552, "alliance_power"): [
            _row(27_991_893_823, "001.png", 1, "[3DNG] 3色团子"),
            _row(23_873_369_613, "001.png", 2, "[nLs] naturals"),
            _row(23_575_109_261, "001.png", 3, "[sgk] Are you happy"),
            _row(22_992_042_788, "001.png", 4, "[PHL] ももあ連合"),
            _row(20_477_544_820, "001.png", 5, "[oAo] 桜梅桃李"),
            _row(79_085_297_891, "001.png", 7, "[BwD] 八于9团4"),
            _row(19_376_397_986, "001.png", 6, "[ZNU] Ultra familiar"),
            _row(12_747_228_849, "001.png", 8, "[AFZ] AntFighterz"),
        ]
    }

    result = apply_ranking_power_sanity_guard(grouped)

    powers = [row["power"] for row in result[(552, "alliance_power")]]
    assert 79_085_297_891 not in powers
    quarantine = result[("REVIEW", "ranking_guard_quarantine")]
    assert len(quarantine) == 1
    assert quarantine[0]["power"] == 79_085_297_891
    assert quarantine[0]["quarantine_reason"] == "alliance_power_sanity_outlier"
    assert "alliance_power_outlier" in quarantine[0]["ranking_guard_warning"]


def test_alliance_power_legitimate_low_power_tail_is_allowed():
    grouped = {
        (552, "alliance_power"): [
            _row(896_061_016, "004.png", 26),
            _row(880_224_595, "004.png", 27),
            _row(827_574_513, "004.png", 28),
            _row(821_848_668, "004.png", 29),
            _row(747_337_757, "004.png", 30),
            _row(726_980_250, "004.png", 31),
            _row(673_643_806, "004.png", 32),
        ]
    }

    result = apply_ranking_power_sanity_guard(grouped)

    assert ("REVIEW", "ranking_guard_quarantine") not in result
    assert len(result[(552, "alliance_power")]) == 7


def test_first_rank_alliance_power_gets_grace_for_real_leader():
    grouped = {
        (999, "alliance_power"): [
            _row(80_000_000_000, "001.png", 1),
            _row(24_000_000_000, "001.png", 2),
            _row(23_500_000_000, "001.png", 3),
            _row(22_900_000_000, "001.png", 4),
            _row(21_000_000_000, "001.png", 5),
            _row(20_000_000_000, "001.png", 6),
        ]
    }

    result = apply_ranking_power_sanity_guard(grouped)

    assert ("REVIEW", "ranking_guard_quarantine") not in result
    assert len(result[(999, "alliance_power")]) == 6


def test_top_three_alliance_power_rows_are_boundary_aware():
    grouped = {
        (552, "alliance_power"): [
            _row(79_085_297_891, "001.png", 1, "[BwD] 八于9团4"),
            _row(77_709_655_122, "001.png", 2, "[PAN] 己九CIIHNEKOPANC"),
            _row(23_575_109_261, "001.png", 6, "[sgk] Are you happy"),
            _row(22_992_042_788, "001.png", 7, "[PHL] ももあ連合"),
            _row(20_477_544_820, "001.png", 8, "[oAo] 桜梅桃李"),
            _row(70_057_779_917, "002.png", 3, "[uiz] Eureka"),
            _row(9_547_751_408, "002.png", 11, "[247] Team三井"),
            _row(9_034_957_176, "002.png", 12, "[Kfp] 力-礼"),
            _row(8_366_236_376, "002.png", 13, "[nc] 命0母"),
            _row(8_132_533_405, "002.png", 14, "[ZA3W] Apple"),
        ]
    }

    result = apply_ranking_power_sanity_guard(grouped)

    powers = [row["power"] for row in result[(552, "alliance_power")]]
    assert 79_085_297_891 in powers
    assert 77_709_655_122 in powers
    assert 70_057_779_917 in powers
    assert ("REVIEW", "ranking_guard_quarantine") not in result


def test_alliance_power_top_rank_absolute_ceiling_still_quarantines():
    grouped = {
        (552, "alliance_power"): [
            _row(790_000_000_000, "001.png", 1, "[BAD] impossible"),
            _row(77_709_655_122, "001.png", 2, "[PAN] 己九CIIHNEKOPANC"),
            _row(23_575_109_261, "001.png", 6, "[sgk] Are you happy"),
            _row(22_992_042_788, "001.png", 7, "[PHL] ももあ連合"),
            _row(20_477_544_820, "001.png", 8, "[oAo] 桜梅桃李"),
        ]
    }

    result = apply_ranking_power_sanity_guard(grouped)

    quarantine = result[("REVIEW", "ranking_guard_quarantine")]
    assert len(quarantine) == 1
    assert quarantine[0]["power"] == 790_000_000_000
    assert "absolute_power_ceiling" in quarantine[0]["ranking_guard_warning"]


def test_early_source_alliance_power_top_values_are_allowed_without_rank_anchor():
    grouped = {
        (552, "alliance_power"): [
            _row(79_085_297_891, "001.png", None, "[BwD] 八于9团4"),
            _row(77_709_655_122, "001.png", None, "[PAN] 己九CIIHNEKOPANC"),
            _row(27_991_893_823, "001.png", None, "[3DNG] 3色团子"),
            _row(23_873_369_613, "001.png", None, "[nLs] naturals"),
            _row(23_575_109_261, "001.png", None, "[sgk] Are you happy"),
            _row(70_057_779_917, "002.png", None, "[uiz] Eureka"),
            _row(9_547_751_408, "002.png", None, "[247] Team三井"),
            _row(9_034_957_176, "002.png", None, "[Kfp] 力-礼"),
            _row(8_366_236_376, "002.png", None, "[nc] 命0母"),
            _row(8_132_533_405, "002.png", None, "[ZA3W] Apple"),
        ]
    }

    result = apply_ranking_power_sanity_guard(grouped)

    powers = [row["power"] for row in result[(552, "alliance_power")]]
    assert 79_085_297_891 in powers
    assert 77_709_655_122 in powers
    assert 70_057_779_917 in powers
    assert ("REVIEW", "ranking_guard_quarantine") not in result


def test_late_source_alliance_power_high_value_without_rank_anchor_is_still_quarantined():
    grouped = {
        (552, "alliance_power"): [
            _row(27_991_893_823, "001.png", None),
            _row(23_873_369_613, "001.png", None),
            _row(23_575_109_261, "001.png", None),
            _row(22_992_042_788, "001.png", None),
            _row(20_477_544_820, "001.png", None),
            _row(8_000_000_000, "003.png", None),
            _row(7_500_000_000, "003.png", None),
            _row(70_000_000_000, "003.png", None),
            _row(7_000_000_000, "003.png", None),
            _row(6_500_000_000, "003.png", None),
        ]
    }

    result = apply_ranking_power_sanity_guard(grouped)

    quarantine = result[("REVIEW", "ranking_guard_quarantine")]
    assert len(quarantine) == 1
    assert quarantine[0]["power"] == 70_000_000_000
    assert "alliance_power_outlier" in quarantine[0]["ranking_guard_warning"]
