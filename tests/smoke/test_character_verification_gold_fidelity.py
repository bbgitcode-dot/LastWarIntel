from parser.character_verification import analyze_player_name_characters, analyze_alliance_tag_characters


def test_exact_name_with_confusable_characters_is_not_a_gold_blocker_by_default():
    plan = analyze_player_name_characters("LOVE BIEN", "LOVE BIEN")
    assert not plan.required
    assert plan.to_json() == "[]"


def test_known_confusable_drift_targets_only_changed_characters():
    plan = analyze_player_name_characters("Joncollins21", "Joncollinszl")
    assert plan.required
    targets = [(f.position, f.expected, f.observed, f.reason, f.group) for f in plan.findings]
    assert targets == [
        (10, "2", "z", "same_confusion_family_difference", "2zZ"),
        (11, "1", "l", "same_confusion_family_difference", "1lI|"),
    ]


def test_alliance_tags_remain_case_sensitive():
    plan = analyze_alliance_tag_characters("PbC", "PBC")
    assert plan.required
    assert [(f.position, f.expected, f.observed, f.reason) for f in plan.findings] == [
        (1, "b", "B", "case_sensitive_tag_difference")
    ]
