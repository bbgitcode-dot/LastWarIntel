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
