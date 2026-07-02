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
    ambiguous = [row for row in quarantine if row["power"] == 79_085_297_891][0]
    assert ambiguous["power_recovery_status"] == "ambiguous"
    assert ambiguous["power_recovery_decision_strategy"] == "context_candidate_margin"
    assert ambiguous["power_recovery_legacy_used"] is False
    assert ambiguous["power_recovery_candidates"]


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


def test_first_rank_alliance_power_gets_grace_for_real_leader_below_high_cluster_floor():
    grouped = {
        (999, "alliance_power"): [
            _row(49_000_000_000, "001.png", 1),
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


def test_source_shape_blocks_false_552_alliance_power_high_cluster():
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
    assert 79_085_297_891 not in powers
    assert 77_709_655_122 not in powers
    assert 70_057_779_917 not in powers
    quarantine = result.get(("REVIEW", "ranking_guard_quarantine"), [])
    reviewed_or_recovered = quarantine + result[(552, "alliance_power")]
    assert any(row.get("power_recovery_candidates") for row in reviewed_or_recovered)


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
    assert any(row["power"] == 790_000_000_000 for row in quarantine)
    assert any("absolute_power_ceiling" in row["ranking_guard_warning"] for row in quarantine if row["power"] == 790_000_000_000)


def test_early_source_alliance_power_false_high_values_are_blocked_without_rank_anchor():
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
    assert 79_085_297_891 not in powers
    assert 77_709_655_122 not in powers
    assert 70_057_779_917 not in powers
    quarantine = result.get(("REVIEW", "ranking_guard_quarantine"), [])
    reviewed_or_recovered = quarantine + result[(552, "alliance_power")]
    assert any(row.get("power_recovery_candidates") for row in reviewed_or_recovered)


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

    powers = [row["power"] for row in result[(552, "alliance_power")]]
    assert 70_000_000_000 not in powers
    quarantine = result[("REVIEW", "ranking_guard_quarantine")]
    ambiguous = [row for row in quarantine if row["power"] == 70_000_000_000][0]
    assert ambiguous["power_recovery_status"] == "ambiguous"
    assert ambiguous["power_recovery_decision_strategy"] == "context_candidate_margin"
    assert ambiguous["power_recovery_legacy_used"] is False
    assert ambiguous["power_recovery_candidates"]


def test_general_top_of_source_alliance_power_values_are_allowed_without_rank_anchor():
    grouped = {
        (550, "alliance_power"): [
            _row(19_567_083_952, "550_top.png", None, "[WARF] Whiskeyand Warfare"),
            _row(13_490_123_049, "550_top.png", None, "[LsC] Last Standing Crew"),
            _row(6_730_012_492, "550_top.png", None, "[0] OysFunctional Legion"),
            _row(3_199_527_639, "550_top.png", None, "[PCMS] The Laugh of Death"),
            _row(2_916_999_957, "550_top.png", None, "[P4X] LA PAIX"),
        ],
        (551, "alliance_power"): [
            _row(5_320_326_083, "551_mid.png", None, "[Hsg] Hit squad"),
            _row(3_429_840_690, "551_mid.png", None, "[ItI] one eye raven"),
            _row(1_927_716_551, "551_mid.png", None, "[647] sikistff"),
            _row(1_449_620_285, "551_mid.png", None, "[GRm] Garam r Korea"),
            _row(1_436_117_971, "551_mid.png", None, "[ALY] Mhammad Al"),
        ],
    }

    result = apply_ranking_power_sanity_guard(grouped)

    assert ("REVIEW", "ranking_guard_quarantine") not in result
    assert len(result[(550, "alliance_power")]) == 5
    assert len(result[(551, "alliance_power")]) == 5


def test_general_top_of_source_allowance_does_not_bless_late_row_outlier():
    grouped = {
        (550, "alliance_power"): [
            _row(6_730_012_492, "550_top.png", None, "[0] OysFunctional Legion"),
            _row(3_199_527_639, "550_top.png", None, "[PCMS] The Laugh of Death"),
            _row(19_567_083_952, "550_top.png", None, "[WARF] Whiskeyand Warfare"),
            _row(2_916_999_957, "550_top.png", None, "[P4X] LA PAIX"),
            _row(1_607_939_782, "550_top.png", None, "[NeX] 550"),
        ]
    }

    result = apply_ranking_power_sanity_guard(grouped)

    quarantine = result[("REVIEW", "ranking_guard_quarantine")]
    assert len(quarantine) == 1
    assert quarantine[0]["power"] == 19_567_083_952


def test_server553_thp_digit_explosion_cluster_blocks_all_high_rows_even_with_one_missing_rank_conflict():
    grouped = {
        (553, "total_hero_power"): [
            _row(764_292_586, "553_late.png", 100, "[LAFA] chris711"),
            _row(764_047_047, "553_late.png", 103, "[LAFA] Pel Cowboy from Hell"),
            _row(763_106_065, "553_late.png", 107, "[SWSQ] st34km4n"),
            # This is the regression row from v0.9.5.43: no explicit late rank
            # warning was available, but it is part of the same impossible high cluster.
            _row(762_831_270, "553_late.png", None, "[SWSQ] Crank40"),
            _row(164_292_586, "553_late.png", 100, "[LAFA] chris711"),
            _row(164_047_047, "553_late.png", 103, "[LAFA] Pel Cowboy from Hell"),
            _row(163_645_571, "553_late.png", 104, "[SBrO] StealthNinja"),
            _row(163_415_086, "553_late.png", 105, "[IxN] khs"),
        ]
    }

    result = apply_ranking_power_sanity_guard(grouped)

    trusted_powers = {row["power"] for row in result[(553, "total_hero_power")]}
    assert {764_292_586, 764_047_047, 763_106_065, 762_831_270}.isdisjoint(trusted_powers)
    # v0.9.5.52 adds an OCR error probability model. Rows whose exact
    # leading-digit correction clearly wins may now recover; rows without enough
    # rank/context separation still remain quarantined.
    assert {164_292_586, 164_047_047, 163_106_065}.issubset(trusted_powers)
    recovered = [row for row in result[(553, "total_hero_power")] if row.get("power_recovered_from") == 763_106_065][0]
    assert recovered["power"] == 163_106_065
    assert recovered["power_recovery_decision_version"] == "v0.9.5.52"
    # .52 may recover the whole compact high cluster when each row has a clear
    # context candidate; the key invariant is that no 7xxM value reaches
    # Operational Truth.
    quarantine = result.get(("REVIEW", "ranking_guard_quarantine"), [])
    assert all(row["power"] != 762_831_270 for row in result[(553, "total_hero_power")])


def test_server553_alliance_power_middle_77b_spike_is_quarantined_without_screenshot_order():
    grouped = {
        (553, "alliance_power"): [
            _row(27_880_814_562, "553_ap_top.png", None, "[SWSq] Suprema Wave Squad"),
            _row(25_796_108_798, "553_ap_top.png", None, "[LaFa] La Familia"),
            _row(18_410_437_934, "553_ap_top.png", None, "[SBrO] Brothers of Shadows"),
            _row(17_254_654_410, "553_ap_top.png", None, "[AnUW] AnUkrainianWarrior"),
            _row(77_739_565_950, "553_ap_top.png", None, "[kk7] Barb"),
            _row(10_410_414_985, "553_ap_top.png", None, "[IxN] The Iron Nilfgaard"),
            _row(9_555_599_544, "553_ap_top.png", None, "[WWU] Westwärts United"),
        ]
    }

    result = apply_ranking_power_sanity_guard(grouped)

    trusted_powers = {row["power"] for row in result[(553, "alliance_power")]}
    assert 77_739_565_950 not in trusted_powers
    ambiguous = [row for row in result[("REVIEW", "ranking_guard_quarantine")] if row["power"] == 77_739_565_950][0]
    assert ambiguous["power_recovery_status"] == "ambiguous"
    assert ambiguous["power_recovery_decision_strategy"] == "context_candidate_margin"
    assert ambiguous["power_recovery_legacy_used"] is False
    assert ambiguous["power_recovery_candidates"]


def test_context_candidate_recovery_selects_224m_when_local_rank_context_is_clear():
    grouped = {
        (553, "total_hero_power"): [
            _row(430_000_000, "000_first.png", 1),
            _row(410_000_000, "000_first.png", 2),
            _row(390_000_000, "000_first.png", 3),
            _row(225_100_000, "553_context.png", 99),
            _row(764_292_586, "553_context.png", 100),
            _row(223_900_000, "553_context.png", 101),
            _row(223_800_000, "553_context.png", 102),
            _row(224_100_000, "553_context.png", 103),
        ]
    }

    result = apply_ranking_power_sanity_guard(grouped)

    recovered = [row for row in result[(553, "total_hero_power")] if row.get("power_recovered_from") == 764_292_586][0]
    assert recovered["power"] == 224_292_586
    assert recovered["power_recovery_method"] == "total_hero_power_context_candidate_recovery"
    assert recovered["power_recovery_decision_strategy"] == "context_candidate_margin"
    assert recovered["power_recovery_legacy_used"] is False
    assert recovered["power_recovery_candidates"]
    assert ("REVIEW", "ranking_guard_quarantine") not in result


def test_context_candidate_recovery_selects_alliance_candidate_when_clear():
    grouped = {
        (553, "alliance_power"): [
            _row(28_100_000_000, "553_ap_context.png", 1),
            _row(27_900_000_000, "553_ap_context.png", 2),
            _row(77_739_565_950, "553_ap_context.png", 3),
            _row(27_100_000_000, "553_ap_context.png", 4),
            _row(26_900_000_000, "553_ap_context.png", 5),
        ]
    }

    result = apply_ranking_power_sanity_guard(grouped)

    recovered = [row for row in result[(553, "alliance_power")] if row.get("power_recovered_from") == 77_739_565_950][0]
    assert recovered["power"] == 27_739_565_950
    assert recovered["power_recovery_method"] == "alliance_power_context_candidate_recovery"
    assert recovered["power_recovery_decision_strategy"] == "context_candidate_margin"
    assert recovered["power_recovery_legacy_used"] is False
    assert recovered["power_recovery_candidates"]
    assert ("REVIEW", "ranking_guard_quarantine") not in result


def test_low_truncation_recovery_selects_x10_candidate_when_clear():
    grouped = {
        (551, "total_hero_power"): [
            _row(420_000_000, "000_first.png", 1),
            _row(410_000_000, "000_first.png", 2),
            _row(322_000_000, "551_low.png", 94),
            _row(32_030_601, "551_low.png", 95, "[IVE] MEITTi"),
            _row(317_000_000, "551_low.png", 96),
            _row(310_000_000, "551_low.png", 97),
        ]
    }

    result = apply_ranking_power_sanity_guard(grouped)

    recovered = [row for row in result[(551, "total_hero_power")] if row.get("power_recovered_from") == 32_030_601][0]
    assert recovered["power"] == 320_306_010
    assert recovered["power_recovery_decision_version"] == "v0.9.5.52"
    assert recovered["power_recovery_legacy_used"] is False
    assert any(candidate.get("digit_preservation_score", 0) > 0 for candidate in recovered["power_recovery_candidates"])
    assert any("digit_preservation:" in reason for candidate in recovered["power_recovery_candidates"] for reason in candidate["reasons"])
    assert any("scale_x10_truncated_digit" in reason for candidate in recovered["power_recovery_candidates"] for reason in candidate["reasons"])


def test_low_truncation_recovery_quarantines_close_insert_zero_vs_scale_tie():
    grouped = {
        (551, "total_hero_power"): [
            _row(420_000_000, "000_first.png", 1),
            _row(410_000_000, "000_first.png", 2),
            _row(252_000_000, "551_insert_zero.png", 19),
            _row(25_009_089, "551_insert_zero.png", 20, "[IVE] K9 Thunder"),
            _row(248_000_000, "551_insert_zero.png", 21),
            _row(246_000_000, "551_insert_zero.png", 22),
        ]
    }

    result = apply_ranking_power_sanity_guard(grouped)

    trusted = [row for row in result[(551, "total_hero_power")] if row.get("power_recovered_from") == 25_009_089]
    assert trusted == []
    quarantine = result[("REVIEW", "ranking_guard_quarantine")]
    ambiguous = [row for row in quarantine if row["power"] == 25_009_089][0]
    assert ambiguous["power_recovery_status"] == "ambiguous"
    assert ambiguous["power_recovery_decision_version"] == "v0.9.5.52"
    assert ambiguous["power_candidate_margin"] < 0.05


def test_segment_order_tiebreak_recovers_close_high_explosion_candidate():
    grouped = {
        (553, "total_hero_power"): [
            _row(244_865_562, "000_first.png", 1, "[SWSQ] Chris Notty"),
            _row(243_307_296, "000_first.png", 2, "[SWSQ] MegaJuicy"),
            _row(216_226_269, "000_first.png", 3, "[LAFA] Donseponi"),
            _row(171_444_069, "553_segment.png", 54, "[SWSQ] Foxus8g"),
            _row(769_706_374, "553_segment.png", 55, "[SWSQ] KHAN Sale id"),
            _row(170_610_965, "553_segment.png", 56, "[LAFA] Minas Augsburg"),
            _row(170_488_763, "553_segment.png", 57, "[LAFA] Tangooy"),
        ]
    }

    result = apply_ranking_power_sanity_guard(grouped)

    recovered = [row for row in result[(553, "total_hero_power")] if row.get("power_recovered_from") == 769_706_374][0]
    assert recovered["power"] == 170_706_374
    assert "selected_segment_order_candidate" in recovered["power_recovery_selected_reason"]
    assert recovered["power_recovery_decision_version"] == "v0.9.5.52"


def test_low_alliance_power_tail_does_not_get_thp_truncation_recovery():
    grouped = {
        (552, "alliance_power"): [
            _row(63_115_694, "552_ap_tail.png", 21),
            _row(36_733_773, "552_ap_tail.png", 22),
            _row(19_260_818, "552_ap_tail.png", 23),
            _row(13_617_964, "552_ap_tail.png", 24),
            _row(2_046_130, "552_ap_tail.png", 25),
        ]
    }

    result = apply_ranking_power_sanity_guard(grouped)

    assert (552, "alliance_power") in result
    assert [row["power"] for row in result[(552, "alliance_power")]] == [63_115_694, 36_733_773, 19_260_818, 13_617_964, 2_046_130]
    assert ("REVIEW", "ranking_guard_quarantine") not in result
