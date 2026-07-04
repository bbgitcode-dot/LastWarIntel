"""Targeted character verification helpers.

These helpers do not guess or canonicalize identities.  They identify which
visible characters should be re-read from the screenshot because they belong to
known OCR-confusion families or because a case-sensitive alliance tag differs.
The actual Operational Truth value remains unchanged unless future screenshot
re-OCR evidence proves a correction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
import json


CONFUSION_GROUPS: tuple[tuple[str, ...], ...] = (
    ("1", "l", "I", "|"),
    ("2", "z", "Z"),
    ("0", "O", "o"),
    ("5", "S", "s"),
    ("8", "B", "b"),
    ("6", "G"),
    ("9", "g", "q"),
)

_CASE_SENSITIVE_LETTERS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")


@dataclass(frozen=True)
class CharacterVerificationFinding:
    field: str
    position: int
    expected: str = ""
    observed: str = ""
    reason: str = ""
    group: str = ""


@dataclass(frozen=True)
class CharacterVerificationPlan:
    required: bool
    reasons: tuple[str, ...] = ()
    findings: tuple[CharacterVerificationFinding, ...] = field(default_factory=tuple)

    def to_json(self) -> str:
        return json.dumps([finding.__dict__ for finding in self.findings], ensure_ascii=False)

    def reasons_text(self) -> str:
        return ";".join(self.reasons)


def _group_for(char: str) -> tuple[str, ...] | None:
    for group in CONFUSION_GROUPS:
        if char in group:
            return group
    return None


def _same_confusion_family(a: str, b: str) -> bool:
    group_a = _group_for(a)
    group_b = _group_for(b)
    return bool(group_a and group_b and set(group_a) == set(group_b))


def _aligned_differences(expected: str, observed: str) -> list[tuple[int, str, str]]:
    """Return expected-index anchored character differences.

    For equal-length names this is plain position-by-position.  For insertions or
    deletions we still anchor the finding to the nearest expected position so a
    later cropper can inspect that area instead of rereading the whole line.
    """
    expected = expected or ""
    observed = observed or ""
    if len(expected) == len(observed):
        return [(i, e, o) for i, (e, o) in enumerate(zip(expected, observed)) if e != o]

    diffs: list[tuple[int, str, str]] = []
    matcher = SequenceMatcher(a=expected, b=observed)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        span = max(i2 - i1, j2 - j1, 1)
        for offset in range(span):
            pos = min(i1 + offset, max(len(expected) - 1, 0))
            e = expected[i1 + offset] if i1 + offset < i2 else ""
            o = observed[j1 + offset] if j1 + offset < j2 else ""
            diffs.append((pos, e, o))
    return diffs


def analyze_player_name_characters(expected: str, observed: str, *, include_stable_confusables: bool = False) -> CharacterVerificationPlan:
    findings: list[CharacterVerificationFinding] = []
    reasons: list[str] = []
    for pos, exp, obs in _aligned_differences(expected or "", observed or ""):
        if not exp and not obs:
            continue
        group = _group_for(exp) or _group_for(obs)
        if _same_confusion_family(exp, obs):
            reason = "same_confusion_family_difference"
        elif group:
            reason = "ocr_confusable_character_difference"
        else:
            reason = "display_character_difference"
        findings.append(CharacterVerificationFinding(
            field="player_name",
            position=pos,
            expected=exp,
            observed=obs,
            reason=reason,
            group="".join(group or ()),
        ))
        if reason not in reasons:
            reasons.append(reason)

    # v0.9.5.96: Gold-Fidelity mode treats targeted verification as a blocker
    # tool, not a blanket scanner.  A stable but confusable character such as
    # the O in LOVE BIEN is not itself a fidelity problem.  Callers can opt in
    # for exploratory full glyph scanning, but validation defaults to actual
    # display drift only.
    if include_stable_confusables and expected == observed:
        for pos, char in enumerate(observed or ""):
            group = _group_for(char)
            if group:
                findings.append(CharacterVerificationFinding(
                    field="player_name",
                    position=pos,
                    expected=char,
                    observed=char,
                    reason="stable_but_confusable_character",
                    group="".join(group),
                ))
                if "observed_confusable_character" not in reasons:
                    reasons.append("observed_confusable_character")
    return CharacterVerificationPlan(required=bool(findings), reasons=tuple(reasons), findings=tuple(findings))


def analyze_alliance_tag_characters(expected: str, observed: str) -> CharacterVerificationPlan:
    findings: list[CharacterVerificationFinding] = []
    reasons: list[str] = []
    for pos, exp, obs in _aligned_differences(expected or "", observed or ""):
        group = _group_for(exp) or _group_for(obs)
        if exp and obs and exp.upper() == obs.upper() and exp != obs and exp in _CASE_SENSITIVE_LETTERS:
            reason = "case_sensitive_tag_difference"
        elif _same_confusion_family(exp, obs):
            reason = "same_confusion_family_tag_difference"
        elif group:
            reason = "ocr_confusable_tag_character_difference"
        else:
            reason = "tag_character_difference"
        findings.append(CharacterVerificationFinding(
            field="alliance_tag",
            position=pos,
            expected=exp,
            observed=obs,
            reason=reason,
            group="".join(group or ()),
        ))
        if reason not in reasons:
            reasons.append(reason)
    return CharacterVerificationPlan(required=bool(findings), reasons=tuple(reasons), findings=tuple(findings))


def merge_verification_plans(*plans: CharacterVerificationPlan) -> CharacterVerificationPlan:
    findings: list[CharacterVerificationFinding] = []
    reasons: list[str] = []
    for plan in plans:
        findings.extend(plan.findings)
        for reason in plan.reasons:
            if reason not in reasons:
                reasons.append(reason)
    return CharacterVerificationPlan(required=bool(findings), reasons=tuple(reasons), findings=tuple(findings))
