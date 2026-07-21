"""Validate Sentinel OCR output against manually curated ground truth.

The validator compares a Ground Truth Excel file with a Sentinel OCR export.
It is intentionally independent from OCR providers: it measures the result that
actually matters for later Player Mobility and Identity Matching.

Usage:
    python ground_truth_validator.py \
        --ground-truth ground_truth/S6/server_551/top50_THP.xlsx \
        --ocr-output output/lastwar_export.xlsx

Outputs:
    benchmarks/ground_truth_validation_report.xlsx
    benchmarks/ground_truth_validation_report.json
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
import tempfile
import zipfile
import time
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import pandas as pd

from parser.alliance_normalization import build_alliance_vocabulary, normalize_alliance_tag as normalize_alliance_against_vocabulary
from parser.name_normalization import normalize_player_name, normalized_name_similarity
from parser.power_normalization import compare_power
from parser.sequence_alignment import find_best_sequence_candidate
from parser.character_verification import analyze_player_name_characters, analyze_alliance_tag_characters, merge_verification_plans
from parser.targeted_character_reocr import parse_reocr_targets, verify_target_from_screenshot, verify_latin_name_block_from_screenshot, summarize_evidence, filter_local_glyph_targets, CharacterVerificationEvidence
from parser.gap_recovery import annotate_gap_recovery
from parser.gap_resolver import find_cross_server_gap_candidate
from parser.evidence_resolver import find_same_server_evidence_candidate
from inference.context_engine import apply_contextual_inference


DEFAULT_OUTPUT_DIR = Path("benchmarks")

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
ILLEGAL_EXCEL_CHARS_RE = re.compile(r"[\x00-\x08\x0b-\x0c\x0e-\x1f]")
TAG_RE = re.compile(r"^\s*\[\s*([A-Za-z0-9]{2,6})\s*\]\s*(.*)$")


def _count_targets_by_field(targets: list[Any], field: str) -> int:
    return sum(1 for target in targets if getattr(target, "field", "") == field)





def _compact_ascii_key(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", str(text or "")).upper()


def _is_pre_reocr_core_safe(
    *,
    accepted_match: bool,
    name_category: str,
    raw_power_match: bool,
    raw_alliance_match: bool,
    raw_name_display_exact: bool,
    raw_name_normalized_match: bool,
    name_normalized_similarity: float,
    expected_name_latin_core: str,
    actual_name_latin_core: str,
    expected_name_key: str = "",
    actual_name_key: str = "",
) -> tuple[bool, str]:
    """Return whether Core Identity is already strong before expensive ReOCR.

    v0.9.5.123: this is deliberately stricter than the post-ReOCR core gate.
    It is only used to skip low-yield evidence work, never to modify Operational
    Truth or mark full display fidelity as exact.  It protects cases such as
    x Zed/Pumpkin G where rank+power+alliance and a visible Latin core are
    already sufficient for transfer intelligence, while keeping Joncollins21
    eligible for real glyph repair because its 21/zl ending is not a stable
    containment residual before ReOCR.
    """
    if not accepted_match:
        return False, "not_accepted_match"
    if not raw_power_match:
        return False, "power_not_matched"
    if not raw_alliance_match:
        return False, "alliance_not_matched"
    if raw_name_display_exact:
        return True, "display_exact"

    expected_core = _compact_ascii_key(expected_name_latin_core or expected_name_key)
    actual_core = _compact_ascii_key(actual_name_latin_core or actual_name_key)
    if not expected_core or not actual_core or actual_core == "UNKNOWN":
        return False, "missing_or_unknown_core"

    if name_category == "mixed_latin_cjk":
        if raw_name_normalized_match and name_normalized_similarity >= 0.88 and (expected_core in actual_core or actual_core in expected_core or expected_core == actual_core):
            return True, "script_limited_core_preverified"
        return False, "mixed_latin_core_not_stable"

    if name_category == "latin_only":
        if len(expected_core) >= 3 and (expected_core in actual_core or (len(actual_core) >= 4 and actual_core in expected_core)):
            return True, "latin_residual_core_preverified"
        if raw_name_normalized_match and name_normalized_similarity >= 0.965:
            return True, "latin_high_similarity_preverified"
        return False, "latin_core_not_stable"

    return False, "unsupported_name_category"


def _is_low_yield_player_core_target(target: Any, *, core_safe: bool) -> bool:
    """Return True for player-name targets that do not improve Core Truth.

    Full Gold may still care about these glyphs, but the CPU-heavy validator
    should not spend seconds on them during normal Core validation once the
    row's transfer-critical identity is already pre-verified.
    """
    if not core_safe or getattr(target, "field", "") != "player_name":
        return False
    reason = str(getattr(target, "reason", "") or "")
    expected = str(getattr(target, "expected", "") or "")
    observed = str(getattr(target, "observed", "") or "")
    # Case-only or contained-residual glyph probes are cosmetic once the Latin
    # core has already passed the strict pre-ReOCR policy.
    if expected and observed and expected.lower() == observed.lower() and expected != observed:
        return True
    if reason in {"same_confusion_family_difference", "ocr_confusable_character_difference", "display_character_difference"}:
        return True
    return False


# v0.9.5.136 Gold Accuracy Mode
# Accuracy is the default sprint behavior: Scheduler and ReOCR gates may still
# order work, but they must not suppress evidence collection solely to save
# runtime. Promotion remains guarded and Operational Truth remains locked.
GOLD_ACCURACY_MODE = True

def _is_harmless_alliance_case_target(target: Any, *, raw_alliance_match: bool, raw_alliance_case_sensitive_mismatch: bool) -> bool:
    """Return True for low-value alliance case-only probes.

    v0.9.5.122: Core Identity must not spend seconds on re-reading a tag
    whose normalized alliance already matches and whose only difference is
    display case such as ``PbC`` vs ``PBC``. Full Gold still remains blocked
    until display evidence is exact; this gate only avoids expensive ReOCR
    for a non-critical proof.
    """
    if getattr(target, "field", "") != "alliance_tag":
        return False
    reason = str(getattr(target, "reason", "") or "")
    expected = str(getattr(target, "expected", "") or "")
    observed = str(getattr(target, "observed", "") or "")
    return bool(
        raw_alliance_match
        and raw_alliance_case_sensitive_mismatch
        and reason == "case_sensitive_tag_difference"
        and expected
        and observed
        and expected.upper() == observed.upper()
        and expected != observed
    )


def _apply_reocr_budget_gate(
    targets: list[Any],
    *,
    raw_alliance_match: bool,
    raw_alliance_case_sensitive_mismatch: bool,
    raw_name_display_exact: bool,
    raw_name_normalized_match: bool,
    name_normalized_similarity: float,
    raw_power_match: bool,
    pre_core_safe: bool = False,
) -> tuple[list[Any], int, list[str]]:
    """Drop low-yield ReOCR targets before invoking EasyOCR.

    Diagnostic reports showed that alliance tag case probes dominate runtime even
    when the transfer-critical identity is already safe through rank/power/name
    and normalized alliance.  This function is intentionally conservative:
    it only removes alliance case-only targets, never player-name targets and
    never missing/different alliance tags.
    """
    if GOLD_ACCURACY_MODE:
        # v0.9.5.136: runtime-saving gates are disabled in Gold Accuracy Mode.
        # Keep all local targets so Character ReOCR can collect maximum evidence.
        # Nonlocal/script policy remains handled outside this local glyph budget gate.
        return list(targets), 0, ["gold_accuracy_mode_budget_gate_disabled"] if targets else []

    kept: list[Any] = []
    skipped = 0
    reasons: list[str] = []
    identity_core_name_stable = bool(raw_name_display_exact or raw_name_normalized_match or name_normalized_similarity >= 0.88)
    for target in targets:
        if (
            raw_power_match
            and identity_core_name_stable
            and _is_harmless_alliance_case_target(
                target,
                raw_alliance_match=raw_alliance_match,
                raw_alliance_case_sensitive_mismatch=raw_alliance_case_sensitive_mismatch,
            )
        ):
            skipped += 1
            if "budget_skip_alliance_case_only" not in reasons:
                reasons.append("budget_skip_alliance_case_only")
            continue
        if _is_low_yield_player_core_target(target, core_safe=pre_core_safe):
            skipped += 1
            if "budget_skip_core_safe_player_target" not in reasons:
                reasons.append("budget_skip_core_safe_player_target")
            continue
        kept.append(target)
    return kept, skipped, reasons



def _target_cache_key(target: Any, *, expected_text: str, observed_text: str) -> tuple[str, int, str, str, str, str, str]:
    """Build a conservative snapshot-local key for reusable ReOCR evidence.

    v0.9.5.124: Character ReOCR repeatedly validates identical glyph claims
    such as an alliance display repair or a recurring confusion-family target.
    Cache only the exact target/text pair; never generalize across different
    names, positions, or expected/observed glyphs.
    """
    return (
        str(getattr(target, "field", "") or ""),
        int(getattr(target, "position", 0) or 0),
        str(getattr(target, "expected", "") or ""),
        str(getattr(target, "observed", "") or ""),
        str(getattr(target, "reason", "") or ""),
        str(expected_text or ""),
        str(observed_text or ""),
    )


def _cacheable_reocr_evidence(item: Any) -> bool:
    """Return True if an evidence item is safe to reuse within one snapshot.

    Cached evidence is a confidence shortcut, not Operational Truth.  Only
    decisive local glyph outcomes are cached; unresolved/ambiguous/debug-only
    observations are kept uncached so bad geometry does not spread.
    """
    return str(getattr(item, "status", "")) in {"verified_expected", "verified_observed"}


def _clone_cached_reocr_evidence(item: Any, *, target: Any, screenshot: str, row_slot: int | None, expected_text: str, observed_text: str) -> CharacterVerificationEvidence:
    """Return a current-row evidence record derived from snapshot cache.

    The clone deliberately clears crop/vote timing fields and marks provenance
    as an evidence-cache hit.  This avoids pretending that the current crop was
    reread while still letting downstream reports count the verified glyph.
    """
    return CharacterVerificationEvidence(
        field=str(getattr(target, "field", getattr(item, "field", "")) or ""),
        position=int(getattr(target, "position", getattr(item, "position", 0)) or 0),
        expected=str(getattr(target, "expected", getattr(item, "expected", "")) or ""),
        observed=str(getattr(target, "observed", getattr(item, "observed", "")) or ""),
        screenshot=str(screenshot or ""),
        row_slot=row_slot,
        crop_box=None,
        status=str(getattr(item, "status", "")),
        selected=str(getattr(item, "selected", "") or ""),
        confidence=float(getattr(item, "confidence", 0.0) or 0.0),
        votes=tuple(),
        reason="evidence_cache_hit",
        crop_strategy="snapshot_evidence_cache",
        crop_candidate_index=0,
        crop_candidate_count=0,
        crop_candidate_reason="cache_hit",
        crop_anchor_status="cache_hit",
        crop_anchor_text="",
        crop_diagnostic="cache_hit",
        text_length=len(str(expected_text or observed_text or "")),
        expected_text=str(expected_text or ""),
        observed_text=str(observed_text or ""),
        allowed_chars="",
        target_total_ms=0.0,
        crop_generation_ms=0.0,
        variant_build_ms=0.0,
        ocr_read_ms=0.0,
        vote_selection_ms=0.0,
    )

def _evidence_field(item: Any) -> str:
    # v0.9.5.112 hotfix: CharacterVerificationEvidence stores the field
    # directly (item.field).  Older draft code looked for item.target.field,
    # which meant verified_expected evidence was recorded in debug JSON but was
    # never counted when building verified_display_name/tag.  Keep the legacy
    # fallback for any future wrapper objects while preferring the direct field.
    direct = getattr(item, "field", "")
    if direct:
        return str(direct)
    return str(getattr(getattr(item, "target", None), "field", ""))


def _count_evidence_by_field(evidence_items: list[Any], field: str, status: str) -> int:
    return sum(1 for item in evidence_items if _evidence_field(item) == field and getattr(item, "status", "") == status)


def _field_verified_by_reocr(
    *,
    already_exact: bool,
    raw_target_count: int,
    local_target_count: int,
    skipped_target_count: int,
    verified_expected_count: int,
) -> bool:
    if already_exact:
        return True
    if raw_target_count <= 0:
        return False
    if skipped_target_count > 0:
        return False
    if local_target_count <= 0:
        return False
    return verified_expected_count == local_target_count


def _should_run_latin_name_block_reconstruction(
    *,
    accepted_match: bool,
    name_category: str,
    raw_name_display_exact: bool,
    expected_name: str,
    actual_name: str,
    row_slot: int | None,
    raw_power_match: bool,
    raw_alliance_match: bool,
    raw_player_targets: int,
    local_player_targets: int,
    skipped_player_targets: int,
    verified_player_expected: int,
    unresolved_player_evidence: int,
) -> tuple[bool, str]:
    """Gate expensive whole-name reconstruction to high-yield cases only.

    v0.9.5.116 proved that block reconstruction can solve first-contact Latin
    names, but it also ran after successful glyph verification and inflated
    runtime.  v0.9.5.117 only runs the block pass when a Latin-only, aligned row
    still has a real player-name blocker after cheaper glyph evidence.
    """
    if not accepted_match:
        return False, "not_accepted_match"
    if name_category != "latin_only":
        return False, "not_latin_only"
    if raw_name_display_exact:
        return False, "name_already_exact"
    if not expected_name or not actual_name:
        return False, "missing_name_text"
    if str(actual_name).strip().upper() == "UNKNOWN":
        return False, "observed_unknown"
    if row_slot is None:
        return False, "missing_row_slot"
    if not raw_power_match:
        return False, "power_not_matched"
    if not raw_alliance_match:
        return False, "alliance_not_matched"
    if raw_player_targets <= 0:
        return False, "no_player_targets"
    if skipped_player_targets > 0:
        return False, "nonlocal_player_targets_present"
    if local_player_targets <= 0:
        return False, "no_local_player_targets"
    if verified_player_expected >= local_player_targets and unresolved_player_evidence <= 0:
        return False, "glyphs_already_resolved"
    return True, "eligible_player_name_block_residual"



def _is_script_limited_core_identity(
    *,
    accepted_match: bool,
    name_category: str,
    power_match: bool,
    verified_alliance_display_exact: bool,
    raw_name_normalized_match: bool,
    name_normalized_similarity: float,
    expected_name_latin_core: str,
    actual_name_latin_core: str,
) -> tuple[bool, str]:
    """Classify non-Latin display drift without pretending OCR is exact.

    v0.9.5.118: mixed Latin/CJK/Hangul names are often operationally
    identifiable by Server + Power + Alliance + stable Latin core, while the
    full display name remains non-exact. This policy is intentionally narrower
    than full Gold Fidelity: it can clear the Core Identity gate, but it does
    not mark verified_display_name as exact and it does not modify Operational
    Truth.
    """
    if not accepted_match:
        return False, "not_accepted_match"
    if name_category != "mixed_latin_cjk":
        return False, "not_mixed_latin_cjk"
    if not power_match:
        return False, "power_not_matched"
    if not verified_alliance_display_exact:
        return False, "alliance_not_verified"
    if not expected_name_latin_core or not actual_name_latin_core:
        return False, "missing_latin_core"
    if not raw_name_normalized_match:
        return False, "latin_core_not_stable"
    if name_normalized_similarity < 0.88:
        return False, "normalized_similarity_below_policy"
    return True, "script_limited_latin_core_policy"



def _is_latin_residual_core_identity(
    *,
    accepted_match: bool,
    name_category: str,
    power_match: bool,
    verified_alliance_display_exact: bool,
    verified_name_display_exact: bool,
    raw_name_normalized_match: bool,
    name_normalized_similarity: float,
    expected_name_latin_core: str,
    actual_name_latin_core: str,
    expected_name_key: str,
    actual_name_key: str,
    skipped_player_targets: int,
    unresolved_player_evidence: int,
) -> tuple[bool, str]:
    """Classify safe Latin-only residuals after glyph/block OCR.

    v0.9.5.119: by this point DataGuard has already established the row via
    server/power and alliance evidence.  Some Latin-only names remain blocked
    only because OCR injected harmless prefix/suffix noise or missed display
    spacing/case while the stable Latin core is still present (for example
    ``x Zed`` being read as ``XZed 00...``).  This policy clears Core Identity
    only for containment/high-similarity residuals.  It does not mark full
    display fidelity as exact and it does not fix broad missing-glyph cases
    such as ``Drpeek -> Ieek`` or ``N E R D -> NER0``.
    """
    if not accepted_match:
        return False, "not_accepted_match"
    if name_category != "latin_only":
        return False, "not_latin_only"
    if not power_match:
        return False, "power_not_matched"
    if not verified_alliance_display_exact:
        return False, "alliance_not_verified"
    if verified_name_display_exact:
        return False, "name_already_verified"

    expected_core = re.sub(r"[^A-Za-z0-9]", "", str(expected_name_latin_core or "")).upper()
    actual_core = re.sub(r"[^A-Za-z0-9]", "", str(actual_name_latin_core or "")).upper()
    expected_key_clean = re.sub(r"[^A-Za-z0-9]", "", str(expected_name_key or expected_core or "")).upper()
    actual_key_clean = re.sub(r"[^A-Za-z0-9]", "", str(actual_name_key or actual_core or "")).upper()

    if not expected_core or not actual_core:
        return False, "missing_latin_core"
    if len(expected_core) < 3:
        return False, "latin_core_too_short"
    if str(actual_core).upper() == "UNKNOWN":
        return False, "observed_unknown"

    # Exact normalized match is already handled elsewhere.  Here we only clear
    # residuals where the expected player core is visibly contained in the OCR
    # text with extra OCR junk around it, or where the normalized similarity is
    # very high and there are no unresolved local glyph failures.
    containment = expected_core in actual_core or expected_key_clean in actual_key_clean
    reverse_containment = len(actual_core) >= 4 and actual_core in expected_core
    high_similarity_clean = raw_name_normalized_match or name_normalized_similarity >= 0.94

    if containment:
        return True, "latin_residual_core_contained_in_observed"
    if reverse_containment and name_normalized_similarity >= 0.90:
        return True, "latin_residual_observed_contained_in_core"
    if high_similarity_clean and skipped_player_targets == 0 and unresolved_player_evidence == 0:
        return True, "latin_residual_high_similarity_clean"
    return False, "latin_residual_not_stable"

# Unicode ranges useful for high-level reporting. The validator does not need
# to know the user's language; these tags help us measure where OCR struggles.
HAN_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
KANA_RE = re.compile(r"[\u3040-\u30ff]")
HANGUL_RE = re.compile(r"[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]")
LATIN_RE = re.compile(r"[A-Za-z]")


@dataclass(slots=True)
class ValidationSummary:
    ground_truth_rows: int
    ocr_rows: int
    matched_rows: int
    missing_rows: int
    bad_matches: int
    gap_blocks: int
    gap_rows: int
    recoverable_gap_blocks: int
    recoverable_gap_rows: int
    blocked_rank_fallbacks: int
    gap_resolved_rows: int
    unresolved_gap_rows: int
    inference_rows: int
    inference_accepted_rows: int
    precision: float
    recall: float
    f1: float
    validation_server: int | None
    validation_ranking_type: str
    ocr_scope_rows: int
    ocr_total_rows: int
    quarantine_rows: int
    quarantine_scope_rows: int
    ground_truth_quarantined_rows: int
    export_extra_rows: int
    name_exact_matches: int
    name_similarity_avg: float
    name_normalized_similarity_avg: float
    name_normalized_matches: int
    alliance_matches: int
    alliance_exact_matches: int
    alliance_normalized_matches: int
    power_matches: int
    power_exact_matches: int
    power_recovered_matches: int
    rank_matches: int
    usable_identity_matches: int
    player_name_display_exact_matches: int
    alliance_tag_display_exact_matches: int
    exact_identity_matches: int
    identity_risk_rows: int
    high_value_identity_risk_rows: int
    alliance_tag_case_sensitive_mismatches: int
    player_name_drift_rows: int
    identity_fidelity_score: float
    character_verification_candidate_rows: int
    high_value_character_verification_rows: int
    player_name_confusable_drift_rows: int
    alliance_tag_character_verification_rows: int
    gold_fidelity_blocker_rows: int
    player_name_display_drift_rows: int
    alliance_tag_display_drift_rows: int
    power_display_drift_rows: int
    rank_display_drift_rows: int
    gold_fidelity_ready: bool
    character_reocr_target_count: int
    character_reocr_verified_expected: int
    character_reocr_verified_observed: int
    character_reocr_unresolved: int
    character_reocr_skipped_nonlocal: int
    score: float
    verified_name_display_exact_matches: int = 0
    verified_alliance_display_exact_matches: int = 0
    verified_exact_identity_matches: int = 0
    verified_identity_resolution_rows: int = 0
    verified_core_identity_matches: int = 0
    verified_core_identity_resolution_rows: int = 0
    gold_core_blocker_rows: int = 0
    gold_core_ready: bool = False
    script_limited_core_identity_matches: int = 0
    script_limited_core_identity_resolution_rows: int = 0
    latin_residual_core_identity_matches: int = 0
    latin_residual_core_identity_resolution_rows: int = 0


COLUMN_ALIASES = {
    "server": {"server", "warzone"},
    "rank": {"rank", "ranking"},
    "alliance": {"alliance", "alliance_tag", "tag"},
    "power": {"heropower", "hero_power", "power", "thp"},
    "true_name": {"truename", "true_name", "expected_player_name", "expected_name", "player_name_truth"},
    "screenshot": {"screenshot", "source_file", "source"},
    "ocr_name": {"player_name", "ocr_name", "name"},
}


def _canonical_column(name: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(name or "").strip().lower())


def _rename_columns(df: pd.DataFrame, required_kind: str) -> pd.DataFrame:
    reverse: dict[str, str] = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            reverse[_canonical_column(alias)] = canonical

    rename: dict[str, str] = {}
    for column in df.columns:
        key = _canonical_column(column)
        if key in reverse:
            rename[column] = reverse[key]

    df = df.rename(columns=rename)

    if required_kind == "ground_truth":
        required = {"server", "rank", "alliance", "power", "true_name"}
    else:
        # OCR exports may not contain an explicit server column because the
        # server is encoded in the sheet name, e.g. 551_total_hero_power.
        # The loader fills that value after this column-normalization step.
        required = {"rank", "power"}

    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Missing required {required_kind} columns: {missing}. Found columns: {list(df.columns)}")

    return df


def _scalar(value: Any) -> Any:
    """Return a scalar value even when pandas exposes duplicate columns as Series/DataFrame."""
    if isinstance(value, pd.DataFrame):
        if value.empty:
            return ""
        value = value.iloc[:, 0]
    if isinstance(value, pd.Series):
        non_empty = value.dropna()
        if non_empty.empty:
            return ""
        return non_empty.iloc[0]
    return value


def normalize_text(value: Any) -> str:
    value = _scalar(value)
    if value is None or pd.isna(value):
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    text = ANSI_ESCAPE_RE.sub("", text)
    text = ILLEGAL_EXCEL_CHARS_RE.sub("", text)
    text = text.replace("\u3000", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_name(value: Any) -> str:
    text = normalize_text(value)
    match = TAG_RE.match(text)
    if match:
        text = match.group(2)
    return text.strip()


def normalize_tag(value: Any) -> str:
    text = normalize_text(value)
    match = TAG_RE.match(text)
    if match:
        text = match.group(1)
    return text.strip().upper()


def extract_display_tag(value: Any) -> str:
    """Return the visible alliance tag exactly as displayed, preserving case.

    The normal matcher still uses uppercase/canonical tags for row matching, but
    Identity Fidelity must keep Last War tags case-sensitive: DAY and daY are
    different identifiers for historical intelligence.
    """
    text = normalize_text(value)
    match = TAG_RE.match(text)
    if match:
        return match.group(1).strip()
    return text.strip()


def exact_display_match(expected: Any, actual: Any) -> bool:
    return normalize_text(expected) == normalize_text(actual)


def classify_name(value: Any) -> str:
    name = normalize_name(value)
    has_latin = bool(LATIN_RE.search(name))
    has_han = bool(HAN_RE.search(name))
    has_kana = bool(KANA_RE.search(name))
    has_hangul = bool(HANGUL_RE.search(name))
    cjk_count = sum([has_han, has_kana, has_hangul])

    if has_latin and cjk_count:
        return "mixed_latin_cjk"
    if has_hangul and not has_latin and not has_han and not has_kana:
        return "hangul_only"
    if has_kana and not has_latin and not has_han and not has_hangul:
        return "kana_only"
    if has_han and not has_latin and not has_kana and not has_hangul:
        return "han_only"
    if cjk_count and not has_latin:
        return "cjk_mixed"
    if has_latin:
        return "latin_only"
    return "other"


def safe_int(value: Any) -> int | None:
    if pd.isna(value):
        return None
    digits = re.sub(r"[^0-9]", "", str(value))
    if not digits:
        return None
    return int(digits)


def load_ground_truth(path: Path) -> pd.DataFrame:
    book = pd.read_excel(path, sheet_name=None)
    frames = []
    for sheet_name, df in book.items():
        if df.empty:
            continue
        df = _rename_columns(df, "ground_truth")
        df = _collapse_duplicate_columns(df)
        df["ground_truth_sheet"] = sheet_name
        frames.append(df)
    if not frames:
        raise ValueError(f"Ground truth workbook contains no data: {path}")
    gt = pd.concat(frames, ignore_index=True)
    gt["server"] = gt["server"].map(safe_int)
    gt["rank"] = gt["rank"].map(safe_int)
    gt["power"] = gt["power"].map(safe_int)
    gt["alliance_display"] = gt["alliance"].map(extract_display_tag)
    gt["alliance"] = gt["alliance"].map(normalize_tag)
    gt["true_name"] = gt["true_name"].map(normalize_name)
    if "screenshot" in gt.columns:
        gt["screenshot"] = gt["screenshot"].map(normalize_text)
    else:
        gt["screenshot"] = ""
    gt["name_category"] = gt["true_name"].map(classify_name)
    return gt


def _server_from_sheet(sheet_name: str) -> int | None:
    match = re.match(r"(\d{3,4})_", sheet_name)
    return int(match.group(1)) if match else None


def _first_series(df: pd.DataFrame, column_name: str) -> pd.Series | None:
    """Return the first series for a column, even if duplicate labels exist."""
    if column_name not in df.columns:
        return None
    value = df[column_name]
    if isinstance(value, pd.DataFrame):
        return value.iloc[:, 0]
    return value


def _ensure_column_from_aliases(df: pd.DataFrame, target: str, aliases: list[str], default: Any = "") -> pd.DataFrame:
    if target in df.columns:
        series = _first_series(df, target)
        if series is not None:
            df[target] = series
            return df
    for alias in aliases:
        series = _first_series(df, alias)
        if series is not None:
            df[target] = series
            return df
    df[target] = default
    return df


def _collapse_duplicate_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse duplicate Excel column labels by keeping the first non-empty value row-wise.

    Pandas returns a Series when accessing row.get("ocr_name") only when duplicate
    column labels survived import/renaming. The validator works on scalar rows, so
    duplicate labels must be collapsed before validation.
    """
    result = pd.DataFrame(index=df.index)
    for column in dict.fromkeys(df.columns):
        selected = df.loc[:, df.columns == column]
        if selected.shape[1] == 1:
            result[column] = selected.iloc[:, 0]
        else:
            collapsed = selected.bfill(axis=1).iloc[:, 0]
            result[column] = collapsed
    return result


def load_ocr_output(path: Path) -> pd.DataFrame:
    book = pd.read_excel(path, sheet_name=None)
    frames = []
    for sheet_name, df in book.items():
        if df.empty or "total_hero_power" not in sheet_name.lower():
            continue
        df = _rename_columns(df, "ocr_output")
        df = _collapse_duplicate_columns(df)

        # Current Sentinel exports may contain duplicate OCR-name columns after
        # Excel round-tripping. Prefer the normalized OCR/player name and collapse
        # duplicates to a single Series so validation never crashes on duplicate
        # labels.
        df = _ensure_column_from_aliases(df, "ocr_name", ["player_name", "name"], "")
        df = _ensure_column_from_aliases(df, "alliance", ["alliance_tag", "tag"], "")
        df = _collapse_duplicate_columns(df)

        server_series = _first_series(df, "server")
        if server_series is None or server_series.isna().all():
            df["server"] = _server_from_sheet(sheet_name)
        else:
            df["server"] = server_series

        df["ocr_sheet"] = sheet_name
        frames.append(df)
    if not frames:
        raise ValueError(f"OCR workbook contains no Total Hero Power sheets: {path}")
    ocr = pd.concat(frames, ignore_index=True)
    ocr["_ocr_row_id"] = range(len(ocr))
    ocr["server"] = ocr["server"].map(safe_int)
    ocr["rank"] = ocr["rank"].map(safe_int)
    ocr["power"] = ocr["power"].map(safe_int)
    ocr["alliance_display"] = ocr["alliance"].map(extract_display_tag)
    ocr["alliance"] = ocr["alliance"].map(normalize_tag)
    ocr["ocr_name"] = ocr["ocr_name"].map(normalize_name)
    if "source_file" not in ocr.columns:
        ocr["source_file"] = ""
    return ocr



def load_ranking_guard_quarantine(path: Path) -> pd.DataFrame:
    """Load Ranking Guard quarantine rows from a Sentinel export workbook.

    The normal OCR loader intentionally reads only Total Hero Power sheets. For
    operational validation we also need to know whether a Ground Truth row was
    protected by the Ranking Guard instead of silently exported into the wrong
    ranking. This loader keeps quarantine evidence separate from trusted OCR
    output so quarantine can be measured without being treated as Operational
    Truth.
    """
    book = pd.read_excel(path, sheet_name=None)
    frames = []
    for sheet_name, df in book.items():
        if df.empty or "ranking_guard_quarantine" not in sheet_name.lower():
            continue
        df = _collapse_duplicate_columns(df)
        df = _ensure_column_from_aliases(df, "ocr_name", ["player_name", "name"], "")
        df = _ensure_column_from_aliases(df, "alliance", ["alliance_tag", "tag"], "")
        df = _ensure_column_from_aliases(df, "server", ["original_server"], None)
        df = _collapse_duplicate_columns(df)
        df["ocr_sheet"] = sheet_name
        frames.append(df)
    if not frames:
        return pd.DataFrame(columns=[
            "server", "rank", "power", "alliance", "ocr_name", "source_file",
            "ocr_sheet", "expected_ranking_type", "ranking_guard_reason",
            "ranking_guard_warning", "quarantine_reason",
        ])
    quarantine = pd.concat(frames, ignore_index=True)
    quarantine["_quarantine_row_id"] = range(len(quarantine))
    quarantine["server"] = quarantine["server"].map(safe_int)
    quarantine["rank"] = quarantine.get("rank", pd.Series([None] * len(quarantine))).map(safe_int)
    quarantine["power"] = quarantine.get("power", pd.Series([None] * len(quarantine))).map(safe_int)
    quarantine["alliance_display"] = quarantine["alliance"].map(extract_display_tag)
    quarantine["alliance"] = quarantine["alliance"].map(normalize_tag)
    quarantine["ocr_name"] = quarantine["ocr_name"].map(normalize_name)
    if "source_file" not in quarantine.columns:
        quarantine["source_file"] = ""
    for column in ["expected_ranking_type", "ranking_guard_reason", "ranking_guard_warning", "quarantine_reason"]:
        if column not in quarantine.columns:
            quarantine[column] = ""
    return quarantine


def _validation_servers(ground_truth: pd.DataFrame) -> list[int]:
    servers = sorted({int(server) for server in ground_truth.get("server", []) if pd.notna(server)})
    return servers


def _primary_validation_server(ground_truth: pd.DataFrame) -> int | None:
    servers = _validation_servers(ground_truth)
    return servers[0] if len(servers) == 1 else None


def _scope_ocr_to_ground_truth(ground_truth: pd.DataFrame, ocr: pd.DataFrame) -> pd.DataFrame:
    servers = _validation_servers(ground_truth)
    if not servers:
        return ocr
    return ocr[ocr["server"].isin(servers)].copy()


def _find_quarantine_match(gt_row: pd.Series, quarantine: pd.DataFrame, alliance_vocabulary=None) -> tuple[pd.Series | None, str]:
    if quarantine is None or quarantine.empty:
        return None, "not_quarantined"
    expected_server = safe_int(gt_row.get("server"))
    expected_rank = safe_int(gt_row.get("rank"))
    expected_power = safe_int(gt_row.get("power"))
    expected_name = normalize_name(gt_row.get("true_name", ""))
    expected_alliance = normalize_tag(gt_row.get("alliance", ""))
    candidates = quarantine[quarantine["server"] == expected_server]
    if candidates.empty:
        return None, "not_quarantined"

    best = None
    best_score = -1.0
    best_method = "not_quarantined"
    matcher = _alliance_matcher(alliance_vocabulary or build_alliance_vocabulary([]))
    for _, candidate in candidates.iterrows():
        actual_power = safe_int(candidate.get("power"))
        actual_rank = safe_int(candidate.get("rank"))
        actual_name = normalize_name(candidate.get("ocr_name", ""))
        actual_alliance = normalize_tag(candidate.get("alliance", ""))
        power_result = compare_power(expected_power, actual_power)
        name_score = _normalized_similarity(expected_name, actual_name)
        alliance_match = matcher(expected_alliance, actual_alliance)
        rank_match = expected_rank == actual_rank
        score = 0.0
        if power_result.match:
            score += 0.55
        if alliance_match:
            score += 0.20
        if name_score >= 0.88:
            score += 0.20
        elif name_score >= 0.60:
            score += 0.10
        if rank_match:
            score += 0.05
        if score > best_score:
            best = candidate
            best_score = score
            best_method = "ranking_guard_quarantine" if score >= 0.70 else "weak_quarantine_candidate"
    if best is not None and best_method == "ranking_guard_quarantine":
        return best, best_method
    return None, "not_quarantined"

def _similarity(expected: str, actual: str) -> float:
    expected_n = normalize_name(expected).casefold()
    actual_n = normalize_name(actual).casefold()
    if not expected_n and not actual_n:
        return 1.0
    if not expected_n or not actual_n:
        return 0.0
    return SequenceMatcher(None, expected_n, actual_n).ratio()


def _normalized_similarity(expected: str, actual: str) -> float:
    return normalized_name_similarity(normalize_name(expected), normalize_name(actual))


def _alliance_matcher(vocabulary):
    def _matches(expected: str, actual: str) -> bool:
        expected_result = normalize_alliance_against_vocabulary(expected, vocabulary)
        actual_result = normalize_alliance_against_vocabulary(actual, vocabulary)
        return expected_result.value == actual_result.value
    return _matches


def _find_match(gt_row: pd.Series, ocr: pd.DataFrame, alliance_vocabulary=None) -> tuple[pd.Series | None, str, Any | None]:
    server = gt_row["server"]
    rank = gt_row["rank"]
    power = gt_row["power"]
    expected_name = normalize_name(gt_row["true_name"])
    expected_alliance = normalize_tag(gt_row["alliance"])

    candidates = ocr[ocr["server"] == server]

    # First use exact/near/recovered power plus sequence-aware evidence. This
    # prevents shifted OCR ranks from matching the wrong player and lets us
    # recover common OCR-truncated THP values such as 23956100 -> 239561000.
    match, method, sequence_candidate = find_best_sequence_candidate(
        expected_rank=safe_int(rank),
        expected_power=safe_int(power),
        expected_name=expected_name,
        expected_alliance=expected_alliance,
        candidates=candidates,
        normalize_name=normalize_name,
        normalize_tag=normalize_tag,
        name_similarity=_normalized_similarity,
        alliance_match=_alliance_matcher(alliance_vocabulary or build_alliance_vocabulary([])),
    )
    if match is not None:
        return match, method, sequence_candidate

    # Same-server evidence resolver: if the normal sequence matcher refuses a
    # tempting rank fallback, a unique exact-power row may still explain the gap
    # without changing Operational Truth. This captures observed rows with weak
    # identity OCR such as UNKNOWN names while keeping the inference explicit.
    evidence_match, evidence_method, evidence_candidate = find_same_server_evidence_candidate(
        expected_rank=safe_int(rank),
        expected_power=safe_int(power),
        expected_name=expected_name,
        expected_alliance=expected_alliance,
        candidates=candidates,
        normalize_name=normalize_name,
        normalize_tag=normalize_tag,
        name_similarity=_normalized_similarity,
        alliance_match=_alliance_matcher(alliance_vocabulary or build_alliance_vocabulary([])),
    )
    if evidence_match is not None:
        return evidence_match, evidence_method, evidence_candidate

    # Gap resolver: if a screenshot was exported under the wrong server bucket,
    # the correct row can exist outside the expected server. Pull it back only
    # when power plus identity evidence is strong enough.
    gap_match, gap_method, gap_candidate = find_cross_server_gap_candidate(
        expected_server=safe_int(server),
        expected_rank=safe_int(rank),
        expected_power=safe_int(power),
        expected_name=expected_name,
        expected_alliance=expected_alliance,
        all_candidates=ocr,
        normalize_name=normalize_name,
        normalize_tag=normalize_tag,
        name_similarity=_normalized_similarity,
        alliance_match=_alliance_matcher(alliance_vocabulary or build_alliance_vocabulary([])),
    )
    if gap_match is not None:
        return gap_match, gap_method, gap_candidate

    # Rank is only the final fallback. It is useful for review visibility, but it
    # must not become a false positive when both power and name contradict the
    # Ground Truth. A rank-only candidate must still provide at least one strong
    # identity signal.
    by_rank = candidates[candidates["rank"] == rank]
    if not by_rank.empty:
        rank_candidate = by_rank.iloc[0]
        actual_name = normalize_name(rank_candidate.get("ocr_name", rank_candidate.get("player_name", "")))
        actual_alliance = normalize_tag(rank_candidate.get("alliance", rank_candidate.get("alliance_tag", "")))
        actual_power = safe_int(rank_candidate.get("power"))
        nscore = _normalized_similarity(expected_name, actual_name)
        amatch = _alliance_matcher(alliance_vocabulary or build_alliance_vocabulary([]))(expected_alliance, actual_alliance)
        presult = compare_power(power, actual_power)

        if presult.match or nscore >= 0.88 or (amatch and nscore >= 0.55):
            return rank_candidate, "server_rank", None

        # Keep the rejected row in the detail report so the user can inspect why
        # a tempting rank fallback was blocked. This is not counted as a bad
        # match anymore; it is an unresolved gap candidate.
        return rank_candidate, "blocked_rank_fallback", None

    return None, "missing", None

def _ground_truth_row_slots(ground_truth: pd.DataFrame) -> dict[tuple[str, int], int]:
    slots: dict[tuple[str, int], int] = {}
    if "screenshot" not in ground_truth.columns or "rank" not in ground_truth.columns:
        return slots
    for screenshot, group in ground_truth.groupby("screenshot", dropna=False):
        ordered = group.sort_values("rank")
        for slot, (_, row) in enumerate(ordered.iterrows()):
            try:
                slots[(normalize_text(screenshot), int(row["rank"]))] = slot
            except Exception:
                continue
    return slots




def _alignment_score_for_row(row: pd.Series, *, inference_context_gap: bool) -> tuple[float, str, bool, str]:
    """Score whether a row is safe enough for read-only evidence work.

    v0.9.5.128 introduces Alignment Intelligence Phase I.  The score is not a
    match decision and it never changes Operational Truth.  It only records how
    much structural evidence exists for a contextual row so later phases can run
    read-only verification without weakening DataGuard.
    """
    evidence: list[str] = []
    score = 0.0

    if inference_context_gap:
        score += 0.20
        evidence.append("context_gap_detected")
    else:
        score += 0.55
        evidence.append("row_alignment_observed")

    if str(row.get("inference_status", "") or "") == "accepted":
        score += 0.22
        evidence.append("accepted_read_only_inference")
    if str(row.get("gap_recoverable", "") or "").lower() in {"true", "1", "yes"}:
        score += 0.12
        evidence.append("recoverable_bounded_gap")
    gap_reason = str(row.get("gap_reason", "") or "")
    if gap_reason:
        evidence.append(f"gap_reason:{gap_reason}")
    inference_evidence = str(row.get("inference_evidence", "") or "")
    for marker, weight in [
        ("rank_between_trusted_neighbors", 0.10),
        ("tight_bounded_gap", 0.08),
        ("expected_power_fits_neighbor_trend", 0.08),
        ("unsafe_row_match_blocked", 0.05),
    ]:
        if marker in inference_evidence:
            score += weight
            evidence.append(marker)
    try:
        power_similarity = float(row.get("power_similarity", 0.0) or 0.0)
    except (TypeError, ValueError):
        power_similarity = 0.0
    if power_similarity >= 0.98:
        score += 0.05
        evidence.append("high_power_similarity")

    score = min(0.99, round(score, 4))
    read_only_allowed = bool(inference_context_gap and score >= 0.90)
    if read_only_allowed:
        block_reason = "read_only_character_verification_allowed;operational_truth_locked"
    elif inference_context_gap:
        block_reason = "alignment_score_below_read_only_threshold"
    else:
        block_reason = "normal_row_character_verification_policy"
    return score, ";".join(dict.fromkeys(evidence)), read_only_allowed, block_reason


def _build_read_only_alignment_evidence(row: pd.Series) -> str:
    """Build evidence-only payload for high-confidence context gaps.

    v0.9.5.129 executes the read-only lane introduced in v0.9.5.128.  This is
    deliberately not a display resolver and not an Operational Truth update.
    It records the contextual evidence, the suggested Ground Truth display, and
    the OCR/quarantine contradiction that caused the row to remain guarded.
    """
    payload = {
        "status": "executed_read_only_contextual_verification",
        "scope": "evidence_only",
        "operational_truth_modified": False,
        "server": _json_safe(row.get("server")),
        "rank": _json_safe(row.get("rank")),
        "suggested_name_display": normalize_text(row.get("expected_name", "")),
        "suggested_alliance_display": normalize_text(row.get("expected_alliance_display", row.get("expected_alliance", ""))),
        "suggested_power": _json_safe(row.get("expected_power")),
        "observed_name_display": normalize_text(row.get("ocr_name", "")),
        "observed_alliance_display": normalize_text(row.get("ocr_alliance_display", row.get("ocr_alliance", ""))),
        "observed_power": _json_safe(row.get("ocr_power")),
        "quarantine_name": normalize_text(row.get("quarantine_name", "")),
        "quarantine_alliance": normalize_text(row.get("quarantine_alliance", "")),
        "quarantine_power": _json_safe(row.get("quarantine_power")),
        "quarantine_reason": normalize_text(row.get("quarantine_reason", "")),
        "alignment_score": _json_safe(row.get("alignment_score")),
        "inference_confidence": _json_safe(row.get("inference_confidence")),
        "alignment_score_evidence": normalize_text(row.get("alignment_score_evidence", "")),
        "inference_evidence": normalize_text(row.get("inference_evidence", "")),
        "decision": "evidence_collected_no_promotion",
    }
    return json.dumps([payload], ensure_ascii=False)


def _apply_read_only_alignment_execution(guarded: pd.DataFrame, inference_mask: pd.Series) -> pd.DataFrame:
    """Execute the read-only evidence lane for eligible context gaps.

    The execution produces report-only fields. It does not modify verified
    display fields, match fields, exports, snapshots, or Ground Truth.
    """
    if guarded.empty:
        return guarded
    eligible_mask = inference_mask & guarded["verification_allowed_read_only"].astype(bool)
    guarded["read_only_reocr_executed"] = False
    guarded["read_only_reocr_evidence"] = "[]"
    guarded["read_only_suggested_display"] = ""
    guarded["read_only_confidence"] = 0.0
    guarded["read_only_operational_truth_modified"] = False
    if eligible_mask.any():
        guarded.loc[eligible_mask, "read_only_reocr_executed"] = True
        guarded.loc[eligible_mask, "read_only_verification_status"] = "executed_evidence_only_phase2"
        guarded.loc[eligible_mask, "character_reocr_status"] = "executed_read_only_alignment_phase2"
        guarded.loc[eligible_mask, "read_only_reocr_evidence"] = guarded.loc[eligible_mask].apply(_build_read_only_alignment_evidence, axis=1)
        guarded.loc[eligible_mask, "read_only_suggested_display"] = guarded.loc[eligible_mask].apply(
            lambda row: f"{normalize_text(row.get('expected_alliance_display', row.get('expected_alliance', '')))} | {normalize_text(row.get('expected_name', ''))}",
            axis=1,
        )
        guarded.loc[eligible_mask, "read_only_confidence"] = guarded.loc[eligible_mask].apply(
            lambda row: round(max(float(row.get("alignment_score", 0.0) or 0.0), float(row.get("inference_confidence", 0.0) or 0.0)), 4),
            axis=1,
        )
    return guarded


def _apply_alignment_guard(detail: pd.DataFrame) -> pd.DataFrame:
    """Separate contextual alignment gaps from true character fidelity work.

    Contextual inferences are useful for recall/read-only gap explanation, but
    they are not row-level OCR matches. Comparing their Ground Truth identity
    against the rejected neighbouring OCR row creates false Character Re-OCR
    targets such as K9 Thunder vs YUNS.

    v0.9.5.128 kept the strict operational guard while adding Alignment
    Intelligence diagnostics. v0.9.5.129 executes that evidence lane in read-only
    mode: eligible context gaps now receive report-only suggested displays and
    evidence payloads, but Operational Truth remains locked.
    """
    if detail.empty:
        return detail
    guarded = detail.copy()
    inference_mask = guarded["match_method"].astype(str).str.startswith("inference_") | (guarded["failure_class"].astype(str) == "inferred_context_gap")
    guarded["alignment_guard_status"] = "row_alignment_observed"
    guarded.loc[inference_mask, "alignment_guard_status"] = "context_gap_read_only_evidence_gate"
    guarded["alignment_safe_for_character_verification"] = ~inference_mask

    scores = guarded.apply(lambda row: _alignment_score_for_row(row, inference_context_gap=bool(inference_mask.loc[row.name])), axis=1, result_type="expand")
    scores.columns = ["alignment_score", "alignment_score_evidence", "verification_allowed_read_only", "verification_block_reason"]
    guarded = pd.concat([guarded, scores], axis=1)
    guarded["read_only_verification_status"] = "not_applicable"
    guarded.loc[guarded["verification_allowed_read_only"].astype(bool), "read_only_verification_status"] = "eligible_not_executed_phase1"

    if inference_mask.any():
        guarded.loc[inference_mask, "character_verification_candidate"] = guarded.loc[inference_mask, "verification_allowed_read_only"]
        guarded.loc[inference_mask, "high_value_character_verification"] = False
        guarded.loc[inference_mask, "character_verification_reasons"] = "alignment_context_gap_read_only_evidence_only"
        guarded.loc[inference_mask, "character_verification_targets"] = "[]"
        guarded.loc[inference_mask, "player_name_character_verification_targets"] = "[]"
        guarded.loc[inference_mask, "alliance_tag_character_verification_targets"] = "[]"
        guarded.loc[inference_mask, "character_reocr_status"] = "not_executed_read_only_alignment_phase1"
        guarded.loc[inference_mask, "character_reocr_targets"] = 0
        guarded.loc[inference_mask, "character_reocr_verified_expected"] = 0
        guarded.loc[inference_mask, "character_reocr_verified_observed"] = 0
        guarded.loc[inference_mask, "character_reocr_unresolved"] = 0
        guarded.loc[inference_mask, "character_reocr_evidence"] = "[]"
        guarded.loc[inference_mask, "gold_fidelity_blocker"] = False
        guarded.loc[inference_mask, "identity_risk"] = False
        guarded.loc[inference_mask, "identity_risk_reasons"] = "alignment_context_gap_read_only"
        guarded.loc[inference_mask, "high_value_identity_risk"] = False
        guarded.loc[inference_mask, "alignment_context_gap"] = True
    guarded = _apply_read_only_alignment_execution(guarded, inference_mask)
    if "alignment_context_gap" not in guarded.columns:
        guarded["alignment_context_gap"] = False
    guarded["alignment_context_gap"] = guarded["alignment_context_gap"].where(guarded["alignment_context_gap"].notna(), False).astype(bool)
    guarded["verification_allowed_read_only"] = guarded["verification_allowed_read_only"].where(guarded["verification_allowed_read_only"].notna(), False).astype(bool)
    return guarded


def validate(ground_truth: pd.DataFrame, ocr: pd.DataFrame, quarantine: pd.DataFrame | None = None, *, character_reocr_reader=None, screenshots_dir: Path | None = None) -> tuple[ValidationSummary, pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    scoped_ocr = _scope_ocr_to_ground_truth(ground_truth, ocr)
    scoped_quarantine = _scope_ocr_to_ground_truth(ground_truth, quarantine) if quarantine is not None and not quarantine.empty else pd.DataFrame()
    # Validation has access to expected tags, so use the Ground Truth as the
    # authoritative local vocabulary. Do not include OCR-only two-letter shards
    # such as PC/IV here, otherwise they become false exact candidates instead
    # of being corrected to PBC/IVE.
    alliance_vocabulary = build_alliance_vocabulary(ground_truth.get("alliance", []))
    row_slots = _ground_truth_row_slots(ground_truth)
    # v0.9.5.124: snapshot-local evidence cache.  This cache never changes
    # Operational Truth; it only prevents repeated CPU-heavy reads for an
    # identical target/text pair after a decisive local glyph was already seen
    # in this validation run.
    reocr_evidence_cache: dict[tuple[str, int, str, str, str, str, str], Any] = {}
    reocr_cache_stats = {"hits": 0, "misses": 0, "writes": 0, "saved_reocr": 0}
    for _, gt_row in ground_truth.iterrows():
        match, match_method, sequence_candidate = _find_match(gt_row, ocr, alliance_vocabulary)
        expected_name = normalize_name(gt_row["true_name"])
        expected_alliance = normalize_tag(gt_row["alliance"])
        expected_alliance_display = extract_display_tag(gt_row.get("alliance_display", gt_row.get("alliance", "")))
        expected_power = safe_int(gt_row["power"])
        expected_rank = safe_int(gt_row["rank"])

        quarantine_match, quarantine_match_method = _find_quarantine_match(gt_row, scoped_quarantine, alliance_vocabulary)

        if match is None:
            actual_name = ""
            actual_alliance = ""
            actual_alliance_display = ""
            actual_power = None
            actual_rank = None
            source_file = ""
            ocr_sheet = ""
        else:
            actual_name = normalize_name(match.get("ocr_name", ""))
            actual_alliance = normalize_tag(match.get("alliance", ""))
            actual_alliance_display = extract_display_tag(match.get("alliance_display", match.get("alliance", "")))
            actual_power = safe_int(match.get("power"))
            actual_rank = safe_int(match.get("rank"))
            source_file = normalize_text(match.get("source_file", ""))
            ocr_sheet = normalize_text(match.get("ocr_sheet", ""))

        quarantine_name = "" if quarantine_match is None else normalize_name(quarantine_match.get("ocr_name", ""))
        quarantine_alliance = "" if quarantine_match is None else normalize_tag(quarantine_match.get("alliance", ""))
        quarantine_power = None if quarantine_match is None else safe_int(quarantine_match.get("power"))
        quarantine_rank = None if quarantine_match is None else safe_int(quarantine_match.get("rank"))
        quarantine_source_file = "" if quarantine_match is None else normalize_text(quarantine_match.get("source_file", ""))
        quarantine_reason = "" if quarantine_match is None else normalize_text(quarantine_match.get("ranking_guard_reason", quarantine_match.get("quarantine_reason", "")))

        bad_match = str(match_method).startswith("bad_")
        blocked_match = str(match_method) == "blocked_rank_fallback"
        name_similarity = _similarity(expected_name, actual_name)
        name_normalized_similarity = _normalized_similarity(expected_name, actual_name)
        expected_name_normalized = normalize_player_name(expected_name)
        actual_name_normalized = normalize_player_name(actual_name)
        expected_name_key = expected_name_normalized.comparison_key
        actual_name_key = actual_name_normalized.comparison_key
        raw_name_exact = normalize_name(expected_name).casefold() == normalize_name(actual_name).casefold()
        raw_name_display_exact = exact_display_match(expected_name, actual_name)
        raw_name_normalized_match = bool(name_normalized_similarity >= 0.88)
        expected_alliance_result = normalize_alliance_against_vocabulary(expected_alliance, alliance_vocabulary)
        actual_alliance_result = normalize_alliance_against_vocabulary(actual_alliance, alliance_vocabulary)
        expected_alliance_normalized = expected_alliance_result.value
        actual_alliance_normalized = actual_alliance_result.value
        raw_alliance_exact_match = expected_alliance == actual_alliance
        raw_alliance_display_exact_match = expected_alliance_display == actual_alliance_display
        raw_alliance_case_sensitive_mismatch = bool(
            expected_alliance_display
            and actual_alliance_display
            and expected_alliance_display.upper() == actual_alliance_display.upper()
            and expected_alliance_display != actual_alliance_display
        )
        raw_alliance_match = expected_alliance_normalized == actual_alliance_normalized
        raw_alliance_normalized_match = bool(raw_alliance_match and not raw_alliance_exact_match)
        power_result = compare_power(expected_power, actual_power)
        raw_power_match = power_result.match
        raw_power_exact_match = power_result.match_type == "exact"
        raw_power_recovered_match = bool(raw_power_match and not raw_power_exact_match)
        raw_rank_match = expected_rank == actual_rank

        # Effective metrics: rejected rank-only fallbacks are deliberately not
        # counted as valid matches, even if one incidental field happens to fit.
        accepted_match = not bad_match and not blocked_match
        name_exact = bool(raw_name_exact and accepted_match)
        name_display_exact = bool(raw_name_display_exact and accepted_match)
        name_normalized_match = bool(raw_name_normalized_match and accepted_match)
        alliance_exact_match = bool(raw_alliance_exact_match and accepted_match)
        alliance_display_exact_match = bool(raw_alliance_display_exact_match and accepted_match)
        alliance_match = bool(raw_alliance_match and accepted_match)
        alliance_normalized_match = bool(raw_alliance_normalized_match and accepted_match)
        power_match = bool(raw_power_match and accepted_match)
        power_exact_match = bool(raw_power_exact_match and accepted_match)
        power_recovered_match = bool(raw_power_recovered_match and accepted_match)
        rank_match = bool(raw_rank_match and accepted_match)
        usable_identity = bool(match is not None and accepted_match and power_match and alliance_match and max(name_similarity, name_normalized_similarity) >= 0.80)
        exact_identity = bool(accepted_match and rank_match and power_match and alliance_display_exact_match and name_display_exact)
        player_char_plan = analyze_player_name_characters(expected_name, actual_name)
        alliance_char_plan = analyze_alliance_tag_characters(expected_alliance_display, actual_alliance_display)
        character_verification_plan = merge_verification_plans(player_char_plan, alliance_char_plan)
        character_verification_candidate = bool(accepted_match and character_verification_plan.required)
        reocr_evidence_json = "[]"
        reocr_status = "not_requested"
        reocr_summary = {"targets": 0, "verified_expected": 0, "verified_observed": 0, "ambiguous": 0, "unresolved": 0, "skipped_nonlocal": 0}
        evidence_items = []
        raw_targets = parse_reocr_targets(character_verification_plan.to_json())
        local_targets = []
        skipped_targets = 0
        budget_skipped_targets = 0
        budget_gate_reasons: list[str] = []
        gt_screenshot = normalize_text(gt_row.get("screenshot", ""))
        row_slot = row_slots.get((gt_screenshot, expected_rank)) if expected_rank is not None else None
        if character_verification_candidate and screenshots_dir is not None and gt_screenshot:
            screenshot_path = screenshots_dir / gt_screenshot
            local_targets = filter_local_glyph_targets(
                raw_targets,
                expected_name=expected_name,
                observed_name=actual_name,
                expected_alliance=expected_alliance_display,
                observed_alliance=actual_alliance_display,
            )
            pre_core_safe, pre_core_gate_reason = _is_pre_reocr_core_safe(
                accepted_match=accepted_match,
                name_category=str(gt_row.get("name_category", "")),
                raw_power_match=raw_power_match,
                raw_alliance_match=raw_alliance_match,
                raw_name_display_exact=raw_name_display_exact,
                raw_name_normalized_match=raw_name_normalized_match,
                name_normalized_similarity=name_normalized_similarity,
                expected_name_latin_core=expected_name_normalized,
                actual_name_latin_core=actual_name_normalized,
                expected_name_key=expected_name_key,
                actual_name_key=actual_name_key,
            )
            if character_reocr_reader is not None:
                local_targets, budget_skipped_targets, budget_gate_reasons = _apply_reocr_budget_gate(
                    local_targets,
                    raw_alliance_match=raw_alliance_match,
                    raw_alliance_case_sensitive_mismatch=raw_alliance_case_sensitive_mismatch,
                    raw_name_display_exact=raw_name_display_exact,
                    raw_name_normalized_match=raw_name_normalized_match,
                    name_normalized_similarity=name_normalized_similarity,
                    raw_power_match=raw_power_match,
                    pre_core_safe=pre_core_safe,
                )
                if budget_skipped_targets > 0 and pre_core_safe:
                    reason = f"budget_pre_core_safe:{pre_core_gate_reason}"
                    if reason not in budget_gate_reasons:
                        budget_gate_reasons.append(reason)
            skipped_targets = max(0, len(raw_targets) - len(local_targets))
            for target in local_targets:
                expected_text = expected_name if target.field == "player_name" else expected_alliance_display
                observed_text = actual_name if target.field == "player_name" else actual_alliance_display
                cache_key = _target_cache_key(target, expected_text=expected_text, observed_text=observed_text)
                cached_item = reocr_evidence_cache.get(cache_key)
                if cached_item is not None:
                    evidence_items.append(_clone_cached_reocr_evidence(
                        cached_item,
                        target=target,
                        screenshot=gt_screenshot,
                        row_slot=row_slot,
                        expected_text=expected_text,
                        observed_text=observed_text,
                    ))
                    reocr_cache_stats["hits"] += 1
                    reocr_cache_stats["saved_reocr"] += 1
                    continue
                reocr_cache_stats["misses"] += 1
                item = verify_target_from_screenshot(
                    screenshot_path=screenshot_path,
                    target=target,
                    expected_text=expected_text,
                    observed_text=observed_text,
                    row_slot=row_slot,
                    reader=character_reocr_reader,
                )
                evidence_items.append(item)
                if _cacheable_reocr_evidence(item):
                    reocr_evidence_cache[cache_key] = item
                    reocr_cache_stats["writes"] += 1

            # v0.9.5.117: v0.9.5.116 proved whole-name reconstruction works,
            # but it also ran after cheaper glyph verification had already
            # solved the player name.  Gate the expensive block pass to residual
            # Latin-only player-name blockers only.
            player_verified_so_far = _count_evidence_by_field(evidence_items, "player_name", "verified_expected")
            player_unresolved_so_far = _count_evidence_by_field(evidence_items, "player_name", "unresolved")
            run_block_reconstruction, block_reconstruction_gate = _should_run_latin_name_block_reconstruction(
                accepted_match=accepted_match,
                name_category=str(gt_row.get("name_category", "")),
                raw_name_display_exact=raw_name_display_exact,
                expected_name=expected_name,
                actual_name=actual_name,
                row_slot=row_slot,
                raw_power_match=raw_power_match,
                raw_alliance_match=raw_alliance_match,
                raw_player_targets=_count_targets_by_field(raw_targets, "player_name"),
                local_player_targets=_count_targets_by_field(local_targets, "player_name"),
                skipped_player_targets=max(0, _count_targets_by_field(raw_targets, "player_name") - _count_targets_by_field(local_targets, "player_name")),
                verified_player_expected=player_verified_so_far,
                unresolved_player_evidence=player_unresolved_so_far,
            )
            if run_block_reconstruction:
                block_evidence = verify_latin_name_block_from_screenshot(
                    screenshot_path=screenshot_path,
                    expected_text=expected_name,
                    observed_text=actual_name,
                    row_slot=row_slot,
                    reader=character_reocr_reader,
                )
                if getattr(block_evidence, "status", "") == "verified_expected":
                    evidence_items.append(block_evidence)

            reocr_summary = summarize_evidence(evidence_items)
            reocr_summary["skipped_nonlocal"] = skipped_targets
            reocr_evidence_json = json.dumps([item.to_dict() for item in evidence_items], ensure_ascii=False)
            if reocr_summary["targets"] == 0:
                if budget_skipped_targets > 0:
                    reocr_status = "not_requested_policy_budget"
                elif skipped_targets > 0:
                    reocr_status = "not_requested_policy_nonlocal"
                else:
                    reocr_status = "no_targets"
            elif reocr_summary["verified_expected"] == reocr_summary["targets"]:
                reocr_status = "verified_expected"
            elif reocr_summary["verified_observed"] == reocr_summary["targets"]:
                reocr_status = "verified_observed"
            elif reocr_summary["unresolved"] == reocr_summary["targets"]:
                reocr_status = "unresolved"
            else:
                reocr_status = "mixed"

        raw_player_targets = _count_targets_by_field(raw_targets, "player_name")
        raw_alliance_targets = _count_targets_by_field(raw_targets, "alliance_tag")
        local_player_targets = _count_targets_by_field(local_targets, "player_name")
        local_alliance_targets = _count_targets_by_field(local_targets, "alliance_tag")
        skipped_player_targets = max(0, raw_player_targets - local_player_targets)
        skipped_alliance_targets = max(0, raw_alliance_targets - local_alliance_targets)
        verified_player_expected = _count_evidence_by_field(evidence_items, "player_name", "verified_expected")
        verified_alliance_expected = _count_evidence_by_field(evidence_items, "alliance_tag", "verified_expected")

        name_block_verified = any(
            _evidence_field(item) == "player_name"
            and getattr(item, "status", "") == "verified_expected"
            and getattr(item, "reason", "") == "latin_name_block_reconstruction"
            for item in evidence_items
        )
        verified_name_display_exact = bool(accepted_match and (
            name_block_verified
            or _field_verified_by_reocr(
                already_exact=name_display_exact,
                raw_target_count=raw_player_targets,
                local_target_count=local_player_targets,
                skipped_target_count=skipped_player_targets,
                verified_expected_count=verified_player_expected,
            )
        ))
        verified_alliance_display_exact = bool(accepted_match and _field_verified_by_reocr(
            already_exact=alliance_display_exact_match,
            raw_target_count=raw_alliance_targets,
            local_target_count=local_alliance_targets,
            skipped_target_count=skipped_alliance_targets,
            verified_expected_count=verified_alliance_expected,
        ))
        verified_display_name = expected_name if verified_name_display_exact else actual_name
        verified_display_alliance = expected_alliance_display if verified_alliance_display_exact else actual_alliance_display
        # v0.9.5.122: Core Identity can rely on normalized/current-snapshot
        # alliance equivalence. Full display fidelity remains strict and still
        # requires verified_alliance_display_exact. This prevents minutes of
        # CPU-only ReOCR being spent just to prove harmless tag case drift.
        core_alliance_match = bool(verified_alliance_display_exact or alliance_match)
        script_limited_core_identity, script_limited_policy_reason = _is_script_limited_core_identity(
            accepted_match=accepted_match,
            name_category=str(gt_row.get("name_category", "")),
            power_match=power_match,
            verified_alliance_display_exact=core_alliance_match,
            raw_name_normalized_match=raw_name_normalized_match,
            name_normalized_similarity=name_normalized_similarity,
            expected_name_latin_core=expected_name_normalized,
            actual_name_latin_core=actual_name_normalized,
        )
        latin_residual_core_identity, latin_residual_policy_reason = _is_latin_residual_core_identity(
            accepted_match=accepted_match,
            name_category=str(gt_row.get("name_category", "")),
            power_match=power_match,
            verified_alliance_display_exact=core_alliance_match,
            verified_name_display_exact=verified_name_display_exact,
            raw_name_normalized_match=raw_name_normalized_match,
            name_normalized_similarity=name_normalized_similarity,
            expected_name_latin_core=expected_name_normalized,
            actual_name_latin_core=actual_name_normalized,
            expected_name_key=expected_name_key,
            actual_name_key=actual_name_key,
            skipped_player_targets=skipped_player_targets,
            unresolved_player_evidence=_count_evidence_by_field(evidence_items, "player_name", "unresolved"),
        )
        if script_limited_core_identity:
            identity_policy_class = "script_limited_latin_core"
        elif latin_residual_core_identity:
            identity_policy_class = "latin_residual_core"
        else:
            identity_policy_class = "full_display_required"
        # v0.9.5.114 separates full row fidelity from transfer-critical
        # identity fidelity. Rank display drift is still reported, but it no
        # longer hides that Player + Alliance + Power have been verified.
        # v0.9.5.118 adds a narrow policy gate for mixed Latin/CJK/Hangul
        # names: stable Latin core + verified alliance + exact/near power can
        # satisfy Core Identity, while Full Gold remains blocked until display
        # fidelity is exact.
        # v0.9.5.119 adds the analogous *Latin residual* gate for safe
        # containment/high-similarity leftovers such as extra OCR junk around a
        # stable Latin player core.
        verified_exact_identity = bool(accepted_match and rank_match and power_match and verified_name_display_exact and verified_alliance_display_exact)
        verified_core_identity = bool((accepted_match and power_match and verified_name_display_exact and core_alliance_match) or script_limited_core_identity or latin_residual_core_identity)
        verified_identity_resolution = bool(verified_exact_identity and not exact_identity)
        raw_core_identity = bool(accepted_match and power_match and name_display_exact and alliance_display_exact_match)
        verified_core_identity_resolution = bool(verified_core_identity and not raw_core_identity)
        script_limited_core_identity_resolution = bool(script_limited_core_identity and not raw_core_identity)
        latin_residual_core_identity_resolution = bool(latin_residual_core_identity and not raw_core_identity)
        gold_core_blocker = bool(accepted_match and not verified_core_identity)

        identity_risk_reasons = []
        if accepted_match and not verified_name_display_exact:
            identity_risk_reasons.append("player_name_display_drift")
        if script_limited_core_identity:
            identity_risk_reasons.append("script_limited_core_identity")
        if latin_residual_core_identity:
            identity_risk_reasons.append("latin_residual_core_identity")
        if accepted_match and not verified_alliance_display_exact:
            identity_risk_reasons.append("alliance_tag_display_drift")
        if accepted_match and raw_alliance_case_sensitive_mismatch and not verified_alliance_display_exact:
            identity_risk_reasons.append("alliance_tag_case_sensitive_mismatch")
        if usable_identity and not verified_exact_identity:
            identity_risk_reasons.append("fuzzy_or_normalized_identity_not_exact")
        if character_verification_candidate and not verified_exact_identity:
            identity_risk_reasons.append("targeted_character_verification_required")
        gold_fidelity_blocker = bool(accepted_match and not verified_exact_identity)
        if gold_fidelity_blocker:
            identity_risk_reasons.append("gold_fidelity_blocker")
        if accepted_match and verified_core_identity and not verified_exact_identity:
            identity_risk_reasons.append("rank_display_only_full_fidelity_blocker")
        identity_risk = bool(identity_risk_reasons)
        high_value_identity_risk = bool(identity_risk and (expected_rank is not None and expected_rank <= 10))
        high_value_character_verification = bool(character_verification_candidate and (expected_rank is not None and expected_rank <= 10))
        if accepted_match and match_method not in ["missing", "blocked_rank_fallback"]:
            failure_class = "matched"
        elif quarantine_match is not None:
            failure_class = "ranking_guard_quarantine"
        elif blocked_match:
            failure_class = "blocked_rank_fallback"
        elif match is None:
            failure_class = "missing_from_export"
        else:
            failure_class = "unresolved_mismatch"

        rows.append({
            "server": gt_row["server"],
            "rank": expected_rank,
            "expected_alliance": expected_alliance,
            "ocr_alliance": actual_alliance,
            "expected_alliance_display": expected_alliance_display,
            "ocr_alliance_display": actual_alliance_display,
            "expected_alliance_normalized": expected_alliance_normalized,
            "ocr_alliance_normalized": actual_alliance_normalized,
            "alliance_match": alliance_match,
            "alliance_exact_match": alliance_exact_match,
            "alliance_display_exact_match": alliance_display_exact_match,
            "alliance_normalized_match": alliance_normalized_match,
            "alliance_tag_case_sensitive_mismatch": bool(raw_alliance_case_sensitive_mismatch and accepted_match),
            "alliance_match_type": actual_alliance_result.match_type,
            "expected_power": expected_power,
            "ocr_power": actual_power,
            "ocr_power_recovered": power_result.recovered_actual,
            "power_match": power_match,
            "power_exact_match": power_exact_match,
            "power_recovered_match": power_recovered_match,
            "power_match_type": power_result.match_type,
            "power_similarity": round(power_result.similarity, 4),
            "sequence_alignment_score": None if sequence_candidate is None else sequence_candidate.score,
            "expected_name": expected_name,
            "ocr_name": actual_name,
            "expected_name_latin_core": expected_name_normalized.latin_core,
            "ocr_name_latin_core": actual_name_normalized.latin_core,
            "expected_name_key": expected_name_normalized.comparison_key,
            "ocr_name_key": actual_name_normalized.comparison_key,
            "name_exact_match": name_exact,
            "name_display_exact_match": name_display_exact,
            "name_normalized_match": name_normalized_match,
            "name_similarity": round(name_similarity, 4),
            "name_normalized_similarity": round(name_normalized_similarity, 4),
            "usable_identity_match": usable_identity,
            "exact_identity_match": exact_identity,
            "verified_name_display": verified_display_name,
            "verified_alliance_display": verified_display_alliance,
            "verified_name_display_exact_match": verified_name_display_exact,
            "verified_alliance_display_exact_match": verified_alliance_display_exact,
            "core_alliance_match": core_alliance_match,
            "verified_exact_identity_match": verified_exact_identity,
            "verified_identity_resolution": verified_identity_resolution,
            "verified_core_identity_match": verified_core_identity,
            "verified_core_identity_resolution": verified_core_identity_resolution,
            "script_limited_core_identity_match": script_limited_core_identity,
            "script_limited_core_identity_resolution": script_limited_core_identity_resolution,
            "script_limited_policy_reason": script_limited_policy_reason,
            "latin_residual_core_identity_match": latin_residual_core_identity,
            "latin_residual_core_identity_resolution": latin_residual_core_identity_resolution,
            "latin_residual_policy_reason": latin_residual_policy_reason,
            "identity_policy_class": identity_policy_class,
            "gold_core_blocker": gold_core_blocker,
            "identity_risk": identity_risk,
            "identity_risk_reasons": ";".join(dict.fromkeys(identity_risk_reasons)),
            "high_value_identity_risk": high_value_identity_risk,
            "gold_fidelity_blocker": gold_fidelity_blocker,
            "character_verification_candidate": character_verification_candidate,
            "high_value_character_verification": high_value_character_verification,
            "character_verification_reasons": character_verification_plan.reasons_text(),
            "character_verification_targets": character_verification_plan.to_json(),
            "player_name_character_verification_targets": player_char_plan.to_json(),
            "alliance_tag_character_verification_targets": alliance_char_plan.to_json(),
            "character_reocr_status": reocr_status,
            "character_reocr_targets": reocr_summary.get("targets", 0),
            "character_reocr_verified_expected": reocr_summary.get("verified_expected", 0),
            "character_reocr_verified_observed": reocr_summary.get("verified_observed", 0),
            "character_reocr_unresolved": reocr_summary.get("unresolved", 0),
            "character_reocr_skipped_nonlocal": reocr_summary.get("skipped_nonlocal", 0),
            "character_reocr_budget_skipped": budget_skipped_targets,
            "character_reocr_budget_gate_reasons": ";".join(budget_gate_reasons),
            "character_reocr_evidence": reocr_evidence_json,
            "ground_truth_row_slot": row_slot,
            "name_category": gt_row["name_category"],
            "match_method": match_method,
            "bad_match": bad_match,
            "raw_rank_match": raw_rank_match,
            "raw_alliance_match": raw_alliance_match,
            "raw_power_match": raw_power_match,
            "rank_match": rank_match,
            "ocr_rank": actual_rank,
            "failure_class": failure_class,
            "quarantine_match_method": quarantine_match_method,
            "quarantine_rank": quarantine_rank,
            "quarantine_alliance": quarantine_alliance,
            "quarantine_power": quarantine_power,
            "quarantine_name": quarantine_name,
            "quarantine_source_file": quarantine_source_file,
            "quarantine_reason": quarantine_reason,
            "ground_truth_screenshot": normalize_text(gt_row.get("screenshot", "")),
            "ocr_source_file": source_file,
            "ocr_sheet": ocr_sheet,
        })

    detail = pd.DataFrame(rows)
    for key, value in reocr_cache_stats.items():
        detail[f"reocr_evidence_cache_{key}"] = int(value)
    detail, gap_metrics = annotate_gap_recovery(detail)
    detail["valid_match"] = (~detail["match_method"].isin(["missing", "blocked_rank_fallback"])) & (~detail["bad_match"])
    detail, context_inferences = apply_contextual_inference(detail)
    detail = _apply_alignment_guard(detail)
    detail = _apply_display_reconstruction(detail)
    detail = _apply_gold_core_elimination(detail)
    total = len(detail)
    detail["valid_match"] = (~detail["match_method"].isin(["missing", "blocked_rank_fallback"])) & (~detail["bad_match"])
    valid_detail = detail[detail["valid_match"]]
    observed_detail = detail[detail["valid_match"] & ~detail["match_method"].astype(str).str.startswith("inference_")]
    matched = int(len(valid_detail))
    bad_matches = int(detail["bad_match"].sum())
    gap_resolved_rows = int(detail["match_method"].astype(str).str.startswith("gap_").sum())
    inference_rows = int(detail["match_method"].astype(str).str.startswith("inference_").sum())
    ocr_rows = int(len(scoped_ocr))
    ocr_total_rows = int(len(ocr))
    quarantine_rows = int(0 if quarantine is None else len(quarantine))
    quarantine_scope_rows = int(len(scoped_quarantine))
    ground_truth_quarantined_rows = int((detail["failure_class"] == "ranking_guard_quarantine").sum())
    export_extra_rows = max(ocr_rows - matched, 0)
    precision = round(matched / max(ocr_rows, 1), 4)
    recall = round(matched / max(total, 1), 4)
    f1 = round((2 * precision * recall / max(precision + recall, 1e-9)), 4)
    name_exact = int(detail["name_exact_match"].sum())
    normalized_name_matches = int(detail["name_normalized_match"].sum())
    alliance_matches = int(detail["alliance_match"].sum())
    alliance_exact_matches = int(detail["alliance_exact_match"].sum())
    alliance_normalized_matches = int(detail["alliance_normalized_match"].sum())
    power_matches = int(detail["power_match"].sum())
    power_exact_matches = int(detail["power_exact_match"].sum())
    power_recovered_matches = int(detail["power_recovered_match"].sum())
    rank_matches = int(detail["rank_match"].sum())
    usable_matches = int(detail["usable_identity_match"].sum())
    player_name_display_exact_matches = int(detail["name_display_exact_match"].sum())
    alliance_tag_display_exact_matches = int(detail["alliance_display_exact_match"].sum())
    exact_identity_matches = int(detail["exact_identity_match"].sum())
    verified_name_display_exact_matches = int(detail.get("verified_name_display_exact_match", pd.Series(dtype=bool)).sum())
    verified_alliance_display_exact_matches = int(detail.get("verified_alliance_display_exact_match", pd.Series(dtype=bool)).sum())
    verified_exact_identity_matches = int(detail.get("verified_exact_identity_match", pd.Series(dtype=bool)).sum())
    verified_identity_resolution_rows = int(detail.get("verified_identity_resolution", pd.Series(dtype=bool)).sum())
    verified_core_identity_matches = int(detail.get("verified_core_identity_match", pd.Series(dtype=bool)).sum())
    verified_core_identity_resolution_rows = int(detail.get("verified_core_identity_resolution", pd.Series(dtype=bool)).sum())
    script_limited_core_identity_matches = int(detail.get("script_limited_core_identity_match", pd.Series(dtype=bool)).sum())
    script_limited_core_identity_resolution_rows = int(detail.get("script_limited_core_identity_resolution", pd.Series(dtype=bool)).sum())
    latin_residual_core_identity_matches = int(detail.get("latin_residual_core_identity_match", pd.Series(dtype=bool)).sum())
    latin_residual_core_identity_resolution_rows = int(detail.get("latin_residual_core_identity_resolution", pd.Series(dtype=bool)).sum())
    gold_core_blocker_rows = int(detail.get("gold_core_blocker", pd.Series(dtype=bool)).sum())
    identity_risk_rows = int(detail["identity_risk"].sum())
    high_value_identity_risk_rows = int(detail["high_value_identity_risk"].sum())
    alliance_tag_case_sensitive_mismatches = int(detail["alliance_tag_case_sensitive_mismatch"].sum())
    player_name_drift_rows = int((observed_detail.get("name_display_exact_match", pd.Series(dtype=bool)) == False).sum())
    identity_fidelity_score = round((verified_exact_identity_matches / max(total, 1)) * 100, 2)
    character_verification_candidate_rows = int(detail.get("character_verification_candidate", pd.Series(dtype=bool)).sum())
    high_value_character_verification_rows = int(detail.get("high_value_character_verification", pd.Series(dtype=bool)).sum())
    player_name_confusable_drift_rows = int((detail.get("character_verification_candidate", pd.Series(dtype=bool)) & detail.get("character_verification_reasons", pd.Series(dtype=str)).astype(str).str.contains("confusable|same_confusion", regex=True)).sum())
    alliance_tag_character_verification_rows = int(detail.get("alliance_tag_character_verification_targets", pd.Series(dtype=str)).astype(str).ne("[]").sum())
    gold_fidelity_blocker_rows = int(detail.get("gold_fidelity_blocker", pd.Series(dtype=bool)).sum())
    player_name_display_drift_rows = int((observed_detail.get("name_display_exact_match", pd.Series(dtype=bool)) == False).sum())
    alliance_tag_display_drift_rows = int((observed_detail.get("alliance_display_exact_match", pd.Series(dtype=bool)) == False).sum())
    power_display_drift_rows = int((observed_detail.get("power_exact_match", pd.Series(dtype=bool)) == False).sum())
    rank_display_drift_rows = int((observed_detail.get("rank_match", pd.Series(dtype=bool)) == False).sum())
    character_reocr_target_count = int(detail.get("character_reocr_targets", pd.Series(dtype=int)).sum())
    character_reocr_verified_expected = int(detail.get("character_reocr_verified_expected", pd.Series(dtype=int)).sum())
    character_reocr_verified_observed = int(detail.get("character_reocr_verified_observed", pd.Series(dtype=int)).sum())
    character_reocr_unresolved = int(detail.get("character_reocr_unresolved", pd.Series(dtype=int)).sum())
    character_reocr_skipped_nonlocal = int(detail.get("character_reocr_skipped_nonlocal", pd.Series(dtype=int)).sum())
    gold_fidelity_ready = bool(
        matched == total
        and bad_matches == 0
        and gold_fidelity_blocker_rows == 0
        and verified_exact_identity_matches == total
    )
    gold_core_ready = bool(
        matched == total
        and bad_matches == 0
        and gold_core_blocker_rows == 0
        and verified_core_identity_matches == total
    )
    avg_similarity = round(float(detail["name_similarity"].mean()) if total else 0.0, 4)
    avg_normalized_similarity = round(float(detail["name_normalized_similarity"].mean()) if total else 0.0, 4)

    # Score weights direct identity needs: power/rank/alliance establish row,
    # name quality establishes reusable Player Identity.
    score = round((
        (matched / max(total, 1)) * 0.15
        + (power_matches / max(total, 1)) * 0.15
        + (rank_matches / max(total, 1)) * 0.10
        + (alliance_matches / max(total, 1)) * 0.20
        + (name_exact / max(total, 1)) * 0.15
        + (normalized_name_matches / max(total, 1)) * 0.10
        + avg_normalized_similarity * 0.15
    ) * 100, 2)

    summary = ValidationSummary(
        ground_truth_rows=total,
        ocr_rows=ocr_rows,
        matched_rows=matched,
        missing_rows=int((detail["match_method"] == "missing").sum()),
        bad_matches=bad_matches,
        gap_blocks=int(gap_metrics.get("gap_blocks", 0)),
        gap_rows=int(gap_metrics.get("gap_rows", 0)),
        recoverable_gap_blocks=int(gap_metrics.get("recoverable_gap_blocks", 0)),
        recoverable_gap_rows=int(gap_metrics.get("recoverable_gap_rows", 0)),
        blocked_rank_fallbacks=int(gap_metrics.get("blocked_rank_fallbacks", 0)),
        gap_resolved_rows=gap_resolved_rows,
        unresolved_gap_rows=max(int(gap_metrics.get("gap_rows", 0)) - inference_rows, 0),
        inference_rows=inference_rows,
        inference_accepted_rows=len(context_inferences),
        precision=precision,
        recall=recall,
        f1=f1,
        validation_server=_primary_validation_server(ground_truth),
        validation_ranking_type="total_hero_power",
        ocr_scope_rows=ocr_rows,
        ocr_total_rows=ocr_total_rows,
        quarantine_rows=quarantine_rows,
        quarantine_scope_rows=quarantine_scope_rows,
        ground_truth_quarantined_rows=ground_truth_quarantined_rows,
        export_extra_rows=export_extra_rows,
        name_exact_matches=name_exact,
        name_similarity_avg=avg_similarity,
        name_normalized_similarity_avg=avg_normalized_similarity,
        name_normalized_matches=normalized_name_matches,
        alliance_matches=alliance_matches,
        alliance_exact_matches=alliance_exact_matches,
        alliance_normalized_matches=alliance_normalized_matches,
        power_matches=power_matches,
        power_exact_matches=power_exact_matches,
        power_recovered_matches=power_recovered_matches,
        rank_matches=rank_matches,
        usable_identity_matches=usable_matches,
        player_name_display_exact_matches=player_name_display_exact_matches,
        alliance_tag_display_exact_matches=alliance_tag_display_exact_matches,
        exact_identity_matches=exact_identity_matches,
        verified_name_display_exact_matches=verified_name_display_exact_matches,
        verified_alliance_display_exact_matches=verified_alliance_display_exact_matches,
        verified_exact_identity_matches=verified_exact_identity_matches,
        verified_identity_resolution_rows=verified_identity_resolution_rows,
        verified_core_identity_matches=verified_core_identity_matches,
        verified_core_identity_resolution_rows=verified_core_identity_resolution_rows,
        script_limited_core_identity_matches=script_limited_core_identity_matches,
        script_limited_core_identity_resolution_rows=script_limited_core_identity_resolution_rows,
        latin_residual_core_identity_matches=latin_residual_core_identity_matches,
        latin_residual_core_identity_resolution_rows=latin_residual_core_identity_resolution_rows,
        gold_core_blocker_rows=gold_core_blocker_rows,
        gold_core_ready=gold_core_ready,
        identity_risk_rows=identity_risk_rows,
        high_value_identity_risk_rows=high_value_identity_risk_rows,
        alliance_tag_case_sensitive_mismatches=alliance_tag_case_sensitive_mismatches,
        player_name_drift_rows=player_name_drift_rows,
        identity_fidelity_score=identity_fidelity_score,
        character_verification_candidate_rows=character_verification_candidate_rows,
        high_value_character_verification_rows=high_value_character_verification_rows,
        player_name_confusable_drift_rows=player_name_confusable_drift_rows,
        alliance_tag_character_verification_rows=alliance_tag_character_verification_rows,
        gold_fidelity_blocker_rows=gold_fidelity_blocker_rows,
        player_name_display_drift_rows=player_name_display_drift_rows,
        alliance_tag_display_drift_rows=alliance_tag_display_drift_rows,
        power_display_drift_rows=power_display_drift_rows,
        rank_display_drift_rows=rank_display_drift_rows,
        gold_fidelity_ready=gold_fidelity_ready,
        character_reocr_target_count=character_reocr_target_count,
        character_reocr_verified_expected=character_reocr_verified_expected,
        character_reocr_verified_observed=character_reocr_verified_observed,
        character_reocr_unresolved=character_reocr_unresolved,
        character_reocr_skipped_nonlocal=character_reocr_skipped_nonlocal,
        score=score,
    )

    category = detail.groupby("name_category", dropna=False).agg(
        rows=("rank", "count"),
        matched_rows=("valid_match", "sum"),
        name_exact_matches=("name_exact_match", "sum"),
        name_normalized_matches=("name_normalized_match", "sum"),
        avg_name_similarity=("name_similarity", "mean"),
        avg_name_normalized_similarity=("name_normalized_similarity", "mean"),
        alliance_matches=("alliance_match", "sum"),
        alliance_exact_matches=("alliance_exact_match", "sum"),
        alliance_normalized_matches=("alliance_normalized_match", "sum"),
        power_matches=("power_match", "sum"),
        power_exact_matches=("power_exact_match", "sum"),
        power_recovered_matches=("power_recovered_match", "sum"),
        usable_identity_matches=("usable_identity_match", "sum"),
        player_name_display_exact_matches=("name_display_exact_match", "sum"),
        alliance_tag_display_exact_matches=("alliance_display_exact_match", "sum"),
        exact_identity_matches=("exact_identity_match", "sum"),
        verified_exact_identity_matches=("verified_exact_identity_match", "sum"),
        verified_identity_resolution_rows=("verified_identity_resolution", "sum"),
        verified_core_identity_matches=("verified_core_identity_match", "sum"),
        verified_core_identity_resolution_rows=("verified_core_identity_resolution", "sum"),
        script_limited_core_identity_matches=("script_limited_core_identity_match", "sum"),
        script_limited_core_identity_resolution_rows=("script_limited_core_identity_resolution", "sum"),
        latin_residual_core_identity_matches=("latin_residual_core_identity_match", "sum"),
        latin_residual_core_identity_resolution_rows=("latin_residual_core_identity_resolution", "sum"),
        gold_core_blocker_rows=("gold_core_blocker", "sum"),
        identity_risk_rows=("identity_risk", "sum"),
        character_verification_candidate_rows=("character_verification_candidate", "sum"),
        high_value_character_verification_rows=("high_value_character_verification", "sum"),
        gold_fidelity_blocker_rows=("gold_fidelity_blocker", "sum"),
        character_reocr_targets=("character_reocr_targets", "sum"),
        character_reocr_verified_expected=("character_reocr_verified_expected", "sum"),
        character_reocr_skipped_nonlocal=("character_reocr_skipped_nonlocal", "sum"),
    ).reset_index()
    category["avg_name_similarity"] = category["avg_name_similarity"].round(4)

    return summary, detail, category


def _parse_json_list(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    text = str(value)
    if not text or text == "[]" or text.lower() == "nan":
        return []
    try:
        raw = json.loads(text)
    except Exception:
        return []
    return raw if isinstance(raw, list) else []


def _flatten_character_reocr_debug(detail: pd.DataFrame) -> pd.DataFrame:
    """Build a row-per-target debug report for Character ReOCR.

    This report is intentionally diagnostic. It does not alter validation
    metrics or Operational Truth. Its job is to expose whether the current
    failure is row-slot selection, crop geometry, OCR output, or vote selection.
    """
    rows: list[dict[str, Any]] = []
    for _, row in detail.iterrows():
        evidence_items = _parse_json_list(row.get("character_reocr_evidence", "[]"))
        for index, item in enumerate(evidence_items):
            votes = item.get("votes") if isinstance(item, dict) else []
            votes = votes if isinstance(votes, list) else []
            vote_texts = [str(v.get("text", "")) for v in votes if isinstance(v, dict)]
            vote_chars = [str(v.get("char", "")) for v in votes if isinstance(v, dict) and str(v.get("char", ""))]
            vote_variants = [str(v.get("variant", "")) for v in votes if isinstance(v, dict)]
            crop_box = item.get("crop_box") if isinstance(item, dict) else None
            crop_width = crop_height = None
            if isinstance(crop_box, list | tuple) and len(crop_box) == 4:
                try:
                    crop_width = int(crop_box[2]) - int(crop_box[0])
                    crop_height = int(crop_box[3]) - int(crop_box[1])
                except Exception:
                    crop_width = crop_height = None
            rows.append({
                "server": row.get("server"),
                "rank": row.get("rank"),
                "ocr_rank": row.get("ocr_rank"),
                "expected_name": row.get("expected_name"),
                "ocr_name": row.get("ocr_name"),
                "expected_alliance_display": row.get("expected_alliance_display"),
                "ocr_alliance_display": row.get("ocr_alliance_display"),
                "expected_power": row.get("expected_power"),
                "ocr_power": row.get("ocr_power"),
                "match_method": row.get("match_method"),
                "failure_class": row.get("failure_class"),
                "alignment_guard_status": row.get("alignment_guard_status"),
                "alignment_safe_for_character_verification": row.get("alignment_safe_for_character_verification"),
                "character_verification_reasons": row.get("character_verification_reasons"),
                "target_index": index,
                "target_field": item.get("field") if isinstance(item, dict) else "",
                "target_position": item.get("position") if isinstance(item, dict) else None,
                "target_expected": item.get("expected") if isinstance(item, dict) else "",
                "target_observed": item.get("observed") if isinstance(item, dict) else "",
                "target_status": item.get("status") if isinstance(item, dict) else "",
                "selected": item.get("selected") if isinstance(item, dict) else "",
                "confidence": item.get("confidence") if isinstance(item, dict) else 0.0,
                "screenshot": item.get("screenshot") if isinstance(item, dict) else "",
                "row_slot": item.get("row_slot") if isinstance(item, dict) else None,
                "crop_box": json.dumps(crop_box, ensure_ascii=False) if crop_box is not None else "",
                "crop_width": crop_width,
                "crop_height": crop_height,
                "crop_strategy": item.get("crop_strategy") if isinstance(item, dict) else "",
                "crop_anchor_status": item.get("crop_anchor_status") if isinstance(item, dict) else "",
                "crop_anchor_text": item.get("crop_anchor_text") if isinstance(item, dict) else "",
                "crop_diagnostic": item.get("crop_diagnostic") if isinstance(item, dict) else "",
                "text_length": item.get("text_length") if isinstance(item, dict) else None,
                "expected_text": item.get("expected_text") if isinstance(item, dict) else "",
                "observed_text": item.get("observed_text") if isinstance(item, dict) else "",
                "allowed_chars": item.get("allowed_chars") if isinstance(item, dict) else "",
                "target_total_ms": item.get("target_total_ms", 0.0) if isinstance(item, dict) else 0.0,
                "crop_generation_ms": item.get("crop_generation_ms", 0.0) if isinstance(item, dict) else 0.0,
                "variant_build_ms": item.get("variant_build_ms", 0.0) if isinstance(item, dict) else 0.0,
                "ocr_read_ms": item.get("ocr_read_ms", 0.0) if isinstance(item, dict) else 0.0,
                "vote_selection_ms": item.get("vote_selection_ms", 0.0) if isinstance(item, dict) else 0.0,
                "vote_count": len(votes),
                "nonempty_vote_chars": ";".join(vote_chars),
                "vote_variants": ";".join(vote_variants),
                "vote_texts": " | ".join(vote_texts),
                "debug_read": (
                    str(item.get("crop_diagnostic")) if item.get("crop_diagnostic") in {"crop_field_mismatch", "crop_no_text_detected", "vote_outside_allowed_set"} else
                    "no_votes" if len(votes) == 0 else
                    "no_selected_char" if not item.get("selected") else
                    "verified_expected" if item.get("status") == "verified_expected" else
                    "verified_observed" if item.get("status") == "verified_observed" else
                    "ambiguous_or_unresolved"
                ),
            })
    return pd.DataFrame(rows)


def _sanitize_cell(value: Any) -> Any:
    if isinstance(value, str):
        return ILLEGAL_EXCEL_CHARS_RE.sub("", ANSI_ESCAPE_RE.sub("", value))
    return value


def _sanitize_frame(df: pd.DataFrame) -> pd.DataFrame:
    return df.map(_sanitize_cell)



def _json_safe(value: Any) -> Any:
    """Convert pandas/numpy scalar values into JSON-serializable Python types."""
    if isinstance(value, dict):
        return {str(_json_safe(k)): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [_json_safe(v) for v in value]
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except (TypeError, ValueError):
            pass
    return value

def _build_runtime_debug_report(base_metrics: dict[str, float], character_reocr_debug: pd.DataFrame) -> tuple[dict[str, Any], pd.DataFrame]:
    """Build runtime diagnostics for slow validator/ReOCR runs.

    The report is intentionally observational. It does not influence matching,
    inference, ReOCR voting, or Operational Truth.  It simply exposes where the
    wall-clock time is spent so long CPU-only runs can be attacked with data.
    """
    phase_rows: list[dict[str, Any]] = []
    for phase, value in sorted(base_metrics.items()):
        if phase.endswith("_ms"):
            phase_rows.append({"scope": "validator", "phase": phase[:-3], "duration_ms": round(float(value), 3)})

    reocr_summary: dict[str, Any] = {
        "target_rows": int(len(character_reocr_debug)),
        "target_total_ms": 0.0,
        "crop_generation_ms": 0.0,
        "variant_build_ms": 0.0,
        "ocr_read_ms": 0.0,
        "vote_selection_ms": 0.0,
        "avg_target_total_ms": 0.0,
        "slowest_target_ms": 0.0,
        "slowest_target_rank": None,
        "slowest_target_field": "",
        "slowest_target_position": None,
    }
    detail_rows: list[dict[str, Any]] = []
    if not character_reocr_debug.empty:
        timing_cols = ["target_total_ms", "crop_generation_ms", "variant_build_ms", "ocr_read_ms", "vote_selection_ms"]
        work = character_reocr_debug.copy()
        for col in timing_cols:
            if col not in work.columns:
                work[col] = 0.0
            work[col] = pd.to_numeric(work[col], errors="coerce").fillna(0.0)
            reocr_summary[col] = round(float(work[col].sum()), 3)
            phase_rows.append({"scope": "character_reocr", "phase": col[:-3], "duration_ms": reocr_summary[col]})
        reocr_summary["avg_target_total_ms"] = round(float(work["target_total_ms"].mean()), 3)
        if len(work):
            slow_idx = work["target_total_ms"].idxmax()
            slow_row = work.loc[slow_idx]
            reocr_summary["slowest_target_ms"] = round(float(slow_row.get("target_total_ms", 0.0)), 3)
            reocr_summary["slowest_target_rank"] = _json_safe(slow_row.get("rank"))
            reocr_summary["slowest_target_field"] = slow_row.get("target_field", "")
            reocr_summary["slowest_target_position"] = _json_safe(slow_row.get("target_position"))
        group_cols = ["target_field", "target_status", "debug_read"]
        grouped = work.groupby(group_cols, dropna=False).agg(
            rows=("rank", "count"),
            target_total_ms=("target_total_ms", "sum"),
            ocr_read_ms=("ocr_read_ms", "sum"),
            avg_target_total_ms=("target_total_ms", "mean"),
            avg_vote_count=("vote_count", "mean"),
        ).reset_index()
        for col in ["target_total_ms", "ocr_read_ms", "avg_target_total_ms", "avg_vote_count"]:
            grouped[col] = pd.to_numeric(grouped[col], errors="coerce").round(3)
        detail_rows = grouped.to_dict(orient="records")

    payload = {
        "summary": {
            **{key: round(float(value), 3) for key, value in base_metrics.items() if key.endswith("_ms")},
            "character_reocr": reocr_summary,
        },
        "phases": phase_rows,
        "character_reocr_groups": detail_rows,
    }
    runtime_df = pd.DataFrame(phase_rows)
    return payload, runtime_df



def _bool_cell(value: Any) -> bool:
    """Return a stable bool for report cells that may be bool/int/NaN/string."""
    if value is None:
        return False
    try:
        if pd.isna(value):
            return False
    except (TypeError, ValueError):
        pass
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def _int_cell(value: Any) -> int:
    try:
        if value is None or pd.isna(value):
            return 0
    except (TypeError, ValueError):
        pass
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _triage_gold_blocker_row(row: pd.Series) -> dict[str, Any]:
    """Classify a gold-fidelity blocker without changing validation outcome.

    v0.9.5.114 is diagnostic and gate-aware: this triage explains why a row is
    still blocking Gold Fidelity after verified-display resolution.  It must not
    influence matching, DataGuard, inference, ReOCR voting, or Operational Truth.
    """
    name_ok = _bool_cell(row.get("verified_name_display_exact_match"))
    alliance_ok = _bool_cell(row.get("verified_alliance_display_exact_match"))
    rank_ok = _bool_cell(row.get("rank_match"))
    power_ok = _bool_cell(row.get("power_match"))
    power_exact = _bool_cell(row.get("power_exact_match"))
    core_identity_ok = _bool_cell(row.get("verified_core_identity_match")) or (name_ok and alliance_ok and power_ok)
    alignment_gap = _bool_cell(row.get("alignment_context_gap"))
    skipped_nonlocal = _int_cell(row.get("character_reocr_skipped_nonlocal"))
    reocr_unresolved = _int_cell(row.get("character_reocr_unresolved"))
    reocr_targets = _int_cell(row.get("character_reocr_targets"))
    high_value = _bool_cell(row.get("high_value_identity_risk")) or (_int_cell(row.get("rank")) > 0 and _int_cell(row.get("rank")) <= 10)
    category = str(row.get("name_category", "") or "")
    reasons = str(row.get("identity_risk_reasons", "") or "")
    verification_reasons = str(row.get("character_verification_reasons", "") or "")
    player_targets = str(row.get("player_name_character_verification_targets", "") or "")
    alliance_targets = str(row.get("alliance_tag_character_verification_targets", "") or "")

    if alignment_gap:
        blocker_class = "alignment_context_gap_read_only"
        blocker_domain = "row_alignment"
        automation_path = "keep_read_only_context_inference"
        next_action = "Keep conservative: row context is unsafe for character verification. Improve row localization only if this becomes operationally relevant."
    elif core_identity_ok and not rank_ok:
        blocker_class = "identity_core_verified_rank_only_blocker"
        blocker_domain = "rank_display"
        automation_path = "rank_display_gate_cleanup"
        next_action = "Treat as transfer-identity verified. Keep full Gold blocked only for row-fidelity reporting; do not spend OCR glyph budget on this row."
    elif name_ok and alliance_ok and power_ok and not power_exact:
        blocker_class = "identity_core_verified_power_display_blocker"
        blocker_domain = "power_display"
        automation_path = "power_display_reconciliation"
        next_action = "Transfer identity is verified, but power is near/recovered rather than exact. Inspect power display/recovery policy, not names or tags."
    elif name_ok and alliance_ok and (not power_ok):
        blocker_class = "rank_or_power_display_blocker"
        blocker_domain = "rank_power"
        automation_path = "row_rank_power_reconciliation"
        next_action = "Investigate power display drift after verified name/tag; do not spend OCR glyph budget on names or tags."
    elif not name_ok and alliance_ok:
        blocker_domain = "player_name"
        if reocr_unresolved > 0:
            blocker_class = "local_player_glyph_unresolved"
            automation_path = "glyph_crop_refinement"
            next_action = "Refine local player-name glyph crop/voting for remaining Latin confusables."
        elif skipped_nonlocal > 0 or category in {"mixed_latin_cjk", "hangul_only"}:
            blocker_class = "nonlocal_or_multilingual_player_display_drift"
            automation_path = "multilingual_name_ocr_or_conservative_block"
            next_action = "Do not force local glyph correction. Needs stronger multilingual OCR/segmentation or remains conservative."
        elif reocr_targets == 0:
            blocker_class = "player_name_no_local_targets"
            automation_path = "target_generation_review"
            next_action = "Review target generation: blocker has name drift but no safe local glyph targets."
        else:
            blocker_class = "player_name_verified_display_not_exact"
            automation_path = "verified_display_apply_review"
            next_action = "Inspect verified-display apply conditions for this player-name drift."
    elif name_ok and not alliance_ok:
        blocker_domain = "alliance_tag"
        if reocr_unresolved > 0:
            blocker_class = "alliance_tag_reocr_unresolved"
            automation_path = "tag_block_anchor_refinement"
            next_action = "Refine full-tag block anchor/case-sensitive tag glyph voting."
        elif skipped_nonlocal > 0:
            blocker_class = "alliance_tag_nonlocal_or_missing"
            automation_path = "tag_segmentation_review"
            next_action = "Review tag segmentation; do not infer a case-sensitive tag from missing/unsafe evidence."
        else:
            blocker_class = "alliance_tag_verified_display_not_exact"
            automation_path = "verified_tag_apply_review"
            next_action = "Inspect alliance verified-display apply conditions."
    elif not name_ok and not alliance_ok:
        blocker_domain = "player_name_and_alliance_tag"
        if skipped_nonlocal > 0 or category in {"mixed_latin_cjk", "hangul_only"}:
            blocker_class = "combined_nonlocal_multilingual_drift"
            automation_path = "multilingual_row_segmentation"
            next_action = "Treat as complex OCR/segmentation case; avoid automatic identity correction from local glyphs alone."
        elif reocr_unresolved > 0:
            blocker_class = "combined_local_glyph_unresolved"
            automation_path = "glyph_and_tag_crop_refinement"
            next_action = "Refine player glyph and tag block crop; both identity fields still block Gold."
        else:
            blocker_class = "combined_display_apply_or_target_gap"
            automation_path = "target_and_apply_review"
            next_action = "Review target generation and verified-display application for both fields."
    else:
        blocker_class = "unknown_gold_blocker"
        blocker_domain = "unknown"
        automation_path = "manual_diagnostic_review"
        next_action = "Unexpected blocker signature; inspect full detail row."

    return {
        "gold_blocker_class": blocker_class,
        "gold_blocker_domain": blocker_domain,
        "gold_blocker_automation_path": automation_path,
        "gold_blocker_next_action": next_action,
        "gold_blocker_priority": "P1" if high_value else "P2",
        "gold_blocker_is_local_glyph_candidate": blocker_class in {
            "local_player_glyph_unresolved",
            "alliance_tag_reocr_unresolved",
            "combined_local_glyph_unresolved",
        },
        "gold_blocker_is_multilingual_or_nonlocal": "nonlocal" in blocker_class or "multilingual" in blocker_class,
        "gold_blocker_is_structural": blocker_domain in {"row_alignment", "rank_power", "rank_display", "power_display"},
        "gold_blocker_evidence_hint": ";".join(part for part in [reasons, verification_reasons] if part),
        "gold_blocker_player_targets": player_targets,
        "gold_blocker_alliance_targets": alliance_targets,
    }


def _build_gold_blocker_triage(gold_fidelity_blockers: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if gold_fidelity_blockers.empty:
        empty_cols = [
            "gold_blocker_class", "gold_blocker_domain", "gold_blocker_automation_path",
            "gold_blocker_next_action", "gold_blocker_priority", "gold_blocker_is_local_glyph_candidate",
            "gold_blocker_is_multilingual_or_nonlocal", "gold_blocker_is_structural",
            "gold_blocker_evidence_hint", "gold_blocker_player_targets", "gold_blocker_alliance_targets",
        ]
        return pd.DataFrame(columns=list(gold_fidelity_blockers.columns) + empty_cols), pd.DataFrame(columns=[
            "gold_blocker_class", "gold_blocker_domain", "gold_blocker_automation_path", "rows",
            "high_value_rows", "local_glyph_candidate_rows", "multilingual_or_nonlocal_rows", "structural_rows",
            "verified_identity_resolution_rows", "avg_name_similarity", "avg_power_similarity",
        ])

    triage_rows = [_triage_gold_blocker_row(row) for _, row in gold_fidelity_blockers.iterrows()]
    triage = pd.concat([gold_fidelity_blockers.reset_index(drop=True), pd.DataFrame(triage_rows)], axis=1)
    for col in ["verified_core_identity_match", "verified_core_identity_resolution", "script_limited_core_identity_match", "script_limited_core_identity_resolution", "latin_residual_core_identity_match", "latin_residual_core_identity_resolution", "gold_core_blocker"]:
        if col not in triage.columns:
            triage[col] = False
        triage[col] = triage[col].fillna(False).astype(bool)
    for col in ["name_similarity", "power_similarity"]:
        if col not in triage.columns:
            triage[col] = 0.0
        triage[col] = pd.to_numeric(triage[col], errors="coerce").fillna(0.0)
    triage_summary = triage.groupby(["gold_blocker_class", "gold_blocker_domain", "gold_blocker_automation_path"], dropna=False).agg(
        rows=("rank", "count"),
        high_value_rows=("gold_blocker_priority", lambda values: int((values == "P1").sum())),
        local_glyph_candidate_rows=("gold_blocker_is_local_glyph_candidate", "sum"),
        multilingual_or_nonlocal_rows=("gold_blocker_is_multilingual_or_nonlocal", "sum"),
        structural_rows=("gold_blocker_is_structural", "sum"),
        verified_identity_resolution_rows=("verified_identity_resolution", "sum"),
        verified_core_identity_matches=("verified_core_identity_match", "sum"),
        verified_core_identity_resolution_rows=("verified_core_identity_resolution", "sum"),
        script_limited_core_identity_matches=("script_limited_core_identity_match", "sum"),
        script_limited_core_identity_resolution_rows=("script_limited_core_identity_resolution", "sum"),
        latin_residual_core_identity_matches=("latin_residual_core_identity_match", "sum"),
        latin_residual_core_identity_resolution_rows=("latin_residual_core_identity_resolution", "sum"),
        gold_core_blocker_rows=("gold_core_blocker", "sum"),
        avg_name_similarity=("name_similarity", "mean"),
        avg_power_similarity=("power_similarity", "mean"),
    ).reset_index()
    for col in ["avg_name_similarity", "avg_power_similarity"]:
        triage_summary[col] = pd.to_numeric(triage_summary[col], errors="coerce").round(4)
    triage_summary = triage_summary.sort_values(["high_value_rows", "rows"], ascending=[False, False]).reset_index(drop=True)
    return triage, triage_summary


def _classify_gold_core_blocker(row: pd.Series) -> tuple[str, str, str, str]:
    """Classify unresolved Gold Core blockers into actionable triage lanes.

    v0.9.5.126 is diagnostic-first.  These classes do not change matching,
    verified identity, ReOCR voting, inference, or Operational Truth.  They make
    the remaining Gold Core blockers auditable row by row so the next fix can
    be chosen from evidence instead of generic OCR tuning.
    """
    status = str(row.get("row_integrity_status", "") or "")
    blocker_class = str(row.get("gold_blocker_class", "") or "")
    name_category = str(row.get("name_category", "") or "")
    skipped_nonlocal = _int_cell(row.get("character_reocr_skipped_nonlocal"))
    unresolved = _int_cell(row.get("character_reocr_unresolved"))
    observed = _int_cell(row.get("character_reocr_verified_observed"))
    field_mismatch = _int_cell(row.get("evidence_field_mismatch_targets"))
    vote_outside = _int_cell(row.get("evidence_vote_outside_allowed_targets"))
    verified_expected = _int_cell(row.get("character_reocr_verified_expected"))

    if status == "ROW_CONTEXT_GAP" or _bool_cell(row.get("alignment_context_gap")):
        return (
            "context_gap_read_only",
            "row_alignment",
            "not_character_reocr",
            "Keep read-only. Improve row localization/alignment only; do not repair this as glyph drift.",
        )
    if status == "ROW_POLICY_NONLOCAL_REVIEW" or (skipped_nonlocal > 0 and verified_expected == 0 and unresolved == 0 and observed == 0):
        return (
            "policy_nonlocal_script_display",
            "script_display_policy",
            "policy_or_engine",
            "Keep conservative. Needs multilingual/nonlocal display policy or stronger script OCR; do not infer full display from rank/power/alliance.",
        )
    if status == "ROW_OBSERVED_TEXT_CONFIRMED" or observed > 0:
        return (
            "observed_text_confirmed",
            "evidence_against_expected",
            "manual_or_policy",
            "Keep strict. Screenshot-local ReOCR confirmed observed text, so the expected display needs manual review or better benchmark evidence.",
        )
    if status == "ROW_FIELD_MISMATCH_DIAGNOSTIC" or field_mismatch > 0:
        return (
            "crop_geometry_problem",
            "crop_anchor_or_field_bleed",
            "crop_geometry",
            "Fix crop anchor/field isolation before accepting glyph evidence. Do not promote the row while field bleed is present.",
        )
    if status == "ROW_REOCR_UNRESOLVED" or unresolved > 0:
        if skipped_nonlocal > 0 or name_category in {"mixed_latin_cjk", "hangul_only"}:
            return (
                "mixed_local_and_nonlocal_blocker",
                "local_glyph_plus_script_display",
                "split_policy",
                "Split local Latin glyph work from nonlocal script display. Only local glyphs are candidate-solvable; full display remains policy-limited.",
            )
        return (
            "local_glyph_solvable",
            "latin_local_glyph",
            "glyph_crop_refinement",
            "Candidate for local crop/vote refinement. Stay screenshot-local and do not use historical identity memory.",
        )
    if status == "ROW_VOTE_OUTSIDE_ALLOWED_SET" or vote_outside > 0:
        return (
            "vote_warning_gate_review",
            "vote_selection_policy",
            "safe_warning_downgrade_candidate",
            "Review if selected glyph equals expected with high confidence. Downgrade only when the whole Core Identity is otherwise proven.",
        )
    if "nonlocal" in blocker_class or "multilingual" in blocker_class:
        return (
            "policy_nonlocal_script_display",
            "script_display_policy",
            "policy_or_engine",
            "Keep conservative. Needs multilingual/nonlocal display policy or stronger script OCR; do not infer full display from rank/power/alliance.",
        )
    if "local" in blocker_class:
        return (
            "local_glyph_solvable",
            "latin_local_glyph",
            "glyph_crop_refinement",
            "Candidate for local crop/vote refinement. Stay screenshot-local and do not use historical identity memory.",
        )
    return (
        "manual_review",
        "unknown",
        "manual_triage",
        "Unexpected blocker signature. Inspect row evidence before changing validator policy.",
    )


def _build_gold_core_blocker_report(gold_blocker_triage: pd.DataFrame, ocr_evidence_rows: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build the dedicated v0.9.5.126 report for the 15 Gold Core blockers."""
    if gold_blocker_triage.empty:
        cols = [
            "server", "rank", "expected_alliance_display", "ocr_alliance_display",
            "expected_name", "ocr_name", "verified_name_display", "expected_power", "ocr_power",
            "row_integrity_status", "gold_core_failure_class", "gold_core_failure_domain",
            "gold_core_fix_lane", "gold_core_next_safe_action", "gold_blocker_class",
            "gold_blocker_domain", "gold_blocker_automation_path",
        ]
        return pd.DataFrame(columns=cols), pd.DataFrame(columns=["gold_core_failure_class", "rows", "fix_lane", "domain"] )

    core = gold_blocker_triage[gold_blocker_triage.get("gold_core_blocker", False).fillna(False).astype(bool)].copy()
    if core.empty:
        return core, pd.DataFrame(columns=["gold_core_failure_class", "rows", "fix_lane", "domain"] )

    evidence_cols = [
        "server", "rank", "row_integrity_status", "row_integrity_reason",
        "evidence_fragment_rows", "evidence_verified_expected_targets",
        "evidence_verified_observed_targets", "evidence_unresolved_targets",
        "evidence_field_mismatch_targets", "evidence_vote_outside_allowed_targets",
    ]
    available_evidence_cols = [c for c in evidence_cols if c in ocr_evidence_rows.columns]
    if available_evidence_cols:
        core = core.merge(
            ocr_evidence_rows[available_evidence_cols],
            on=["server", "rank"],
            how="left",
            suffixes=("", "_evidence"),
        )

    classified = core.apply(_classify_gold_core_blocker, axis=1, result_type="expand")
    classified.columns = [
        "gold_core_failure_class",
        "gold_core_failure_domain",
        "gold_core_fix_lane",
        "gold_core_next_safe_action",
    ]
    core = pd.concat([core.reset_index(drop=True), classified.reset_index(drop=True)], axis=1)
    core = core.sort_values(["gold_blocker_priority", "rank"], ascending=[True, True]).reset_index(drop=True)

    summary = core.groupby(["gold_core_failure_class", "gold_core_failure_domain", "gold_core_fix_lane"], dropna=False).agg(
        rows=("rank", "count"),
        high_value_rows=("gold_blocker_priority", lambda values: int((values == "P1").sum())),
        min_rank=("rank", "min"),
        max_rank=("rank", "max"),
    ).reset_index().sort_values(["high_value_rows", "rows"], ascending=[False, False]).reset_index(drop=True)
    return core, summary



def _classify_gold_core_resolution_action(row: pd.Series) -> tuple[str, str, str, str, bool]:
    """Convert Gold Core blocker classes into v0.9.5.127 execution lanes.

    This is still diagnostic and planning-only.  It deliberately does not
    promote verified display text, does not mutate Operational Truth, and does
    not treat rank/power/alliance continuity as identity proof.  The purpose is
    to make the next safe engineering step explicit for every blocker row.
    """
    failure_class = str(row.get("gold_core_failure_class", "") or "")
    status = str(row.get("row_integrity_status", "") or "")
    verified_expected = _int_cell(row.get("evidence_verified_expected_targets", row.get("character_reocr_verified_expected")))
    verified_observed = _int_cell(row.get("evidence_verified_observed_targets", row.get("character_reocr_verified_observed")))
    unresolved = _int_cell(row.get("evidence_unresolved_targets", row.get("character_reocr_unresolved")))
    field_mismatch = _int_cell(row.get("evidence_field_mismatch_targets"))
    vote_outside = _int_cell(row.get("evidence_vote_outside_allowed_targets"))
    skipped_nonlocal = _int_cell(row.get("character_reocr_skipped_nonlocal"))
    core_match = _bool_cell(row.get("verified_core_identity_match"))

    if failure_class == "local_glyph_solvable":
        return (
            "P1_LOCAL_GLYPH_RETRY",
            "local_glyph_resolution",
            "Run tighter local glyph crop candidates and require decisive expected-glyph evidence before clearing the blocker.",
            "Local Latin glyph blocker; safe to improve screenshot-local crop/vote mechanics.",
            True,
        )
    if failure_class == "vote_warning_gate_review":
        if verified_expected > 0 and verified_observed == 0 and unresolved == 0 and field_mismatch == 0:
            if core_match:
                return (
                    "P1_WARNING_DOWNGRADE_SAFE",
                    "vote_warning_policy",
                    "Downgrade outside-allowed-set noise to warning when Core Identity is already proven and selected glyph evidence is expected-only.",
                    "Noisy vote environment but expected glyph evidence is decisive and no observed/unresolved/field-mismatch stop sign is present.",
                    True,
                )
            return (
                "P1_WARNING_DOWNGRADE_BLOCKED_BY_CORE",
                "vote_warning_policy",
                "Keep blocked until the row has independent Core Identity proof; do not clear from glyph fragments alone.",
                "Expected glyph evidence exists, but Core Identity is not yet proven end-to-end.",
                False,
            )
        return (
            "P2_WARNING_REVIEW_NEEDS_EVIDENCE",
            "vote_warning_policy",
            "Collect decisive selected-glyph evidence before any warning downgrade is considered.",
            "Vote warning lacks clean expected-only evidence.",
            False,
        )
    if failure_class == "crop_geometry_problem" or status == "ROW_FIELD_MISMATCH_DIAGNOSTIC":
        return (
            "P1_CROP_GEOMETRY_FIRST",
            "crop_geometry",
            "Fix player/tag crop anchoring and field isolation before using the glyph evidence.",
            "Field mismatch or power-column bleed is a hard stop for local glyph acceptance.",
            False,
        )
    if failure_class == "mixed_local_and_nonlocal_blocker":
        return (
            "P1_SPLIT_LOCAL_FROM_SCRIPT",
            "split_policy",
            "Separate local Latin glyph targets from nonlocal script spans; only local targets may be resolved automatically.",
            "Mixed blocker cannot be cleared by a single local glyph rule.",
            False,
        )
    if failure_class == "observed_text_confirmed" or verified_observed > 0:
        return (
            "P2_MANUAL_BENCHMARK_REVIEW",
            "manual_or_benchmark_evidence",
            "Do not override observed evidence. Review screenshot/ground-truth display before changing policy.",
            "ReOCR confirms observed text against expected benchmark display.",
            False,
        )
    if failure_class == "policy_nonlocal_script_display" or skipped_nonlocal > 0:
        return (
            "P2_SCRIPT_POLICY_REQUIRED",
            "script_display_policy",
            "Keep conservative until multilingual display policy or stronger script OCR exists.",
            "Nonlocal script display is outside safe local glyph correction.",
            False,
        )
    if failure_class == "context_gap_read_only":
        return (
            "P2_ALIGNMENT_ONLY",
            "row_alignment",
            "Keep read-only; improve row localization but never run Character ReOCR on context gaps.",
            "Context gaps are not glyph failures.",
            False,
        )
    return (
        "P3_MANUAL_TRIAGE",
        "manual_triage",
        "Inspect complete evidence before changing validator behavior.",
        "Unexpected blocker/action signature.",
        False,
    )


def _build_gold_core_resolution_plan_report(gold_core_blocker_report: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build the v0.9.5.127 safe execution plan from Gold Core blockers."""
    if gold_core_blocker_report.empty:
        cols = [
            "server", "rank", "expected_name", "ocr_name", "verified_name_display",
            "expected_alliance_display", "ocr_alliance_display", "verified_alliance_display",
            "row_integrity_status", "gold_core_failure_class", "gold_core_resolution_action",
            "gold_core_resolution_lane", "gold_core_resolution_next_step",
            "gold_core_resolution_guardrail", "gold_core_local_automation_candidate",
        ]
        return pd.DataFrame(columns=cols), pd.DataFrame(columns=[
            "gold_core_resolution_action", "gold_core_resolution_lane", "rows", "automation_candidate_rows", "high_value_rows", "min_rank", "max_rank",
        ])

    plan = gold_core_blocker_report.copy()
    action = plan.apply(_classify_gold_core_resolution_action, axis=1, result_type="expand")
    action.columns = [
        "gold_core_resolution_action",
        "gold_core_resolution_lane",
        "gold_core_resolution_next_step",
        "gold_core_resolution_guardrail",
        "gold_core_local_automation_candidate",
    ]
    plan = pd.concat([plan.reset_index(drop=True), action.reset_index(drop=True)], axis=1)
    if "gold_blocker_priority" not in plan.columns:
        plan["gold_blocker_priority"] = "P2"
    plan["gold_core_local_automation_candidate"] = plan["gold_core_local_automation_candidate"].fillna(False).astype(bool)
    plan = plan.sort_values(["gold_blocker_priority", "gold_core_resolution_action", "rank"], ascending=[True, True, True]).reset_index(drop=True)
    summary = plan.groupby(["gold_core_resolution_action", "gold_core_resolution_lane"], dropna=False).agg(
        rows=("rank", "count"),
        automation_candidate_rows=("gold_core_local_automation_candidate", "sum"),
        high_value_rows=("gold_blocker_priority", lambda values: int((values == "P1").sum())),
        min_rank=("rank", "min"),
        max_rank=("rank", "max"),
    ).reset_index().sort_values(["high_value_rows", "automation_candidate_rows", "rows"], ascending=[False, False, False]).reset_index(drop=True)
    return plan, summary


def _row_evidence_status(row: pd.Series, row_reocr_debug: pd.DataFrame) -> tuple[str, str]:
    """Classify whether a validation row has trustworthy visual provenance.

    This is diagnostic only.  It does not alter matching, ReOCR voting, DataGuard,
    or Operational Truth.  The goal is to make cases such as a suspected
    Thunder/YUNS row mix-up auditable: did Sentinel read the right row, did crops
    bleed into another field, or is this simply script/OCR display drift?
    """
    if _bool_cell(row.get("alignment_context_gap")):
        return "ROW_CONTEXT_GAP", "contextual inference row; character evidence intentionally blocked"
    if not _bool_cell(row.get("valid_match")):
        return "ROW_NOT_ACCEPTED", "row is not an accepted validator match"
    if str(row.get("alignment_guard_status", "")) not in {"", "row_alignment_observed"}:
        return "ROW_ALIGNMENT_WARNING", str(row.get("alignment_guard_status", ""))
    if row_reocr_debug.empty:
        reocr_status = str(row.get("character_reocr_status", ""))
        if reocr_status == "not_requested_policy_budget":
            # Backward-compatible default for older tests/reports that do not
            # carry explicit Core-Gate columns: budget skips are considered OK
            # unless the row explicitly says Core Identity is blocked.
            if ("verified_core_identity_match" not in row.index and "gold_core_blocker" not in row.index) or (
                _bool_cell(row.get("verified_core_identity_match")) and not _bool_cell(row.get("gold_core_blocker"))
            ):
                return "ROW_OK_POLICY_BUDGET", "ReOCR intentionally skipped by budget gate; core evidence remains available"
            return "ROW_POLICY_BUDGET_REVIEW", "ReOCR skipped by budget policy but Core Identity is still blocked"
        if reocr_status == "not_requested_policy_nonlocal":
            if _bool_cell(row.get("verified_core_identity_match")) and not _bool_cell(row.get("gold_core_blocker")):
                return "ROW_OK_POLICY_NONLOCAL", "nonlocal/multilingual character targets intentionally skipped after core verification"
            return "ROW_POLICY_NONLOCAL_REVIEW", "nonlocal/multilingual targets skipped by policy; Core Identity still requires review"
        if _bool_cell(row.get("character_verification_candidate")):
            return "ROW_EVIDENCE_MISSING", "character verification candidate without ReOCR evidence"
        return "ROW_OK_NO_REOCR", "accepted aligned row; no character evidence required"

    statuses = set(row_reocr_debug.get("target_status", pd.Series(dtype=str)).astype(str))
    diagnostics = set(row_reocr_debug.get("crop_diagnostic", pd.Series(dtype=str)).astype(str))
    anchors = set(row_reocr_debug.get("crop_anchor_status", pd.Series(dtype=str)).astype(str))
    fields = set(row_reocr_debug.get("target_field", pd.Series(dtype=str)).astype(str))

    if "unresolved" in statuses:
        return "ROW_REOCR_UNRESOLVED", "one or more local character targets remain unresolved"
    if "ambiguous_vote" in statuses:
        return "ROW_REOCR_AMBIGUOUS", "one or more local character targets produced ambiguous votes"
    if "verified_observed" in statuses and "player_name" in fields:
        return "ROW_OBSERVED_TEXT_CONFIRMED", "ReOCR confirmed observed player-name glyphs instead of expected glyphs"
    if "crop_field_mismatch" in diagnostics or "field_mismatch" in anchors:
        if _bool_cell(row.get("verified_core_identity_match")) and not _bool_cell(row.get("gold_core_blocker")):
            return "ROW_OK_WITH_CROP_WARNING", "core identity is verified; crop field/power-column bleed kept as warning"
        return "ROW_FIELD_MISMATCH_DIAGNOSTIC", "ReOCR crop evidence reports field/power-column mismatch"
    if "vote_outside_allowed_set" in diagnostics:
        if _bool_cell(row.get("verified_core_identity_match")) and not _bool_cell(row.get("gold_core_blocker")):
            return "ROW_OK_WITH_VOTE_WARNING", "core identity is verified; outside-allowed-set votes kept as warning"
        return "ROW_VOTE_OUTSIDE_ALLOWED_SET", "ReOCR votes include text outside the allowed target set"
    return "ROW_OK_WITH_REOCR", "accepted aligned row with successful local ReOCR evidence"




def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _vote_consensus_score(item: dict[str, Any]) -> float:
    """Return how consistently OCR variants support the selected character.

    This is diagnostic only and feeds the v0.9.5.133 Evidence Confidence
    report fields. It does not alter matching, exports, snapshots, or Ground
    Truth.
    """
    selected = normalize_text(item.get("selected", ""))
    votes = item.get("votes", [])
    if not isinstance(votes, list) or not votes:
        return 0.0
    chars: list[str] = []
    for vote in votes:
        if not isinstance(vote, dict):
            continue
        char = normalize_text(vote.get("char", ""))
        if char:
            chars.append(char[:1])
    if not chars:
        return 0.0
    if not selected:
        return 0.0
    return round(sum(1 for char in chars if char == selected[:1]) / len(chars), 4)


def _ocr_confidence_score(item: dict[str, Any]) -> float:
    direct = _safe_float(item.get("confidence"), 0.0)
    votes = item.get("votes", [])
    vote_values: list[float] = []
    if isinstance(votes, list):
        for vote in votes:
            if isinstance(vote, dict):
                vote_values.append(_safe_float(vote.get("confidence"), 0.0))
    vote_avg = sum(vote_values) / len(vote_values) if vote_values else 0.0
    # OCR vote confidences are often low even for correct glyphs. Keep direct
    # selected confidence dominant, but still expose weak OCR support.
    return round(max(0.0, min(1.0, (direct * 0.75) + (vote_avg * 0.25))), 4)


def _crop_quality_score(item: dict[str, Any]) -> float:
    anchor = str(item.get("crop_anchor_status", "") or "")
    diagnostic = str(item.get("crop_diagnostic", "") or "")
    score = 0.65
    if anchor in {"anchor_seen", "cache_hit"}:
        score += 0.25
    elif anchor in {"text_without_anchor"}:
        score += 0.05
    elif anchor in {"field_mismatch"}:
        score -= 0.25
    if diagnostic in {"crop_anchor_ok", "cache_hit", "verified_expected"}:
        score += 0.1
    if diagnostic in {"crop_power_column_bleed", "crop_field_mismatch", "vote_outside_allowed_set"}:
        score -= 0.15
    return round(max(0.0, min(1.0, score)), 4)


def _unicode_class_score(item: dict[str, Any]) -> float:
    expected = normalize_text(item.get("expected", ""))
    selected = normalize_text(item.get("selected", ""))
    char = (expected or selected)[:1]
    if not char:
        return 0.0
    codepoint = ord(char)
    if codepoint < 128:
        return 1.0
    # Nonlocal glyphs are accepted as evidence, but they need stronger
    # independent support before promotion.
    return 0.78


def _position_stability_score(item: dict[str, Any]) -> float:
    candidate_count = int(_safe_float(item.get("crop_candidate_count"), 0.0))
    candidate_index = int(_safe_float(item.get("crop_candidate_index"), 0.0))
    reason = str(item.get("crop_candidate_reason", "") or "")
    if str(item.get("crop_anchor_status", "")) == "cache_hit":
        return 1.0
    score = 0.75
    if reason in {"base", "tag_block_anchor"}:
        score += 0.15
    if candidate_count and candidate_index >= max(candidate_count - 1, 0):
        score -= 0.1
    return round(max(0.0, min(1.0, score)), 4)


def _fragment_confidence(item: dict[str, Any]) -> tuple[float, dict[str, float]]:
    """Score one character evidence fragment for explainable promotion control."""
    status = str(item.get("status", "") or "")
    status_weight = 1.0 if status == "verified_expected" else (0.45 if status == "verified_observed" else 0.2)
    components = {
        "crop_quality": _crop_quality_score(item),
        "ocr_confidence": _ocr_confidence_score(item),
        "vote_consensus": _vote_consensus_score(item),
        "position_stability": _position_stability_score(item),
        "unicode_class": _unicode_class_score(item),
        "status_weight": round(status_weight, 4),
    }
    weighted = (
        components["crop_quality"] * 0.18
        + components["ocr_confidence"] * 0.24
        + components["vote_consensus"] * 0.24
        + components["position_stability"] * 0.14
        + components["unicode_class"] * 0.08
        + components["status_weight"] * 0.12
    )
    return round(max(0.0, min(1.0, weighted)), 4), components


def _evidence_confidence_summary(items: list[dict[str, Any]], expected_name: str, expected_tag: str, name_applied: int, tag_applied: int, unresolved: int, observed_votes: int, status: str) -> dict[str, Any]:
    scored: list[float] = []
    component_totals: dict[str, list[float]] = {
        "crop_quality": [], "ocr_confidence": [], "vote_consensus": [],
        "position_stability": [], "unicode_class": [], "status_weight": [],
    }
    for item in items:
        if not isinstance(item, dict):
            continue
        score, components = _fragment_confidence(item)
        scored.append(score)
        item["fragment_confidence"] = score
        item["fragment_confidence_components"] = components
        for key, value in components.items():
            component_totals.setdefault(key, []).append(value)
    avg_fragment_confidence = round(sum(scored) / len(scored), 4) if scored else 0.0
    name_len = len(normalize_text(expected_name))
    tag_len = len(normalize_text(expected_tag))
    name_coverage = round(name_applied / name_len, 4) if name_len else (1.0 if status == "already_exact" else 0.0)
    tag_coverage = round(tag_applied / tag_len, 4) if tag_len else 0.0
    if status == "already_exact":
        display_coverage = 1.0
    else:
        denom = max(name_len + tag_len, 1)
        display_coverage = round((name_applied + tag_applied) / denom, 4)
    if status == "contextual_display_suggestion":
        confidence_decision = "suggested_contextual"
    elif status in {"full_display_reconstructed", "name_reconstructed", "alliance_reconstructed"} and not observed_votes and not unresolved and avg_fragment_confidence >= 0.55:
        # A targeted glyph may reconstruct the exact display while touching only
        # one or two positions. Do not punish these narrow, high-quality fixes
        # for low whole-string coverage; the Promotion Guard already blocked
        # unsafe UNKNOWN bases and unresolved fragments before this layer.
        confidence_decision = "eligible"
    elif observed_votes or unresolved or avg_fragment_confidence < 0.55 or display_coverage < 0.5:
        confidence_decision = "blocked_low_evidence"
    elif avg_fragment_confidence < 0.72 or display_coverage < 0.8:
        confidence_decision = "suggested_evidence_only"
    else:
        confidence_decision = "eligible"
    component_avg = {
        f"evidence_avg_{key}": round(sum(values) / len(values), 4) if values else 0.0
        for key, values in component_totals.items()
    }
    return {
        "evidence_fragments_total": len(scored),
        "evidence_confirmed_fragments": sum(1 for item in items if isinstance(item, dict) and str(item.get("status", "")) == "verified_expected"),
        "evidence_observed_fragments": observed_votes,
        "evidence_unresolved_fragments": unresolved,
        "evidence_avg_fragment_confidence": avg_fragment_confidence,
        "display_name_coverage_score": name_coverage,
        "display_alliance_coverage_score": tag_coverage,
        "display_coverage_score": display_coverage,
        "display_confidence_decision": confidence_decision,
        **component_avg,
    }


def _evidence_budget_decision(row: pd.Series, evidence: dict[str, Any], status: str) -> dict[str, Any]:
    """Compute v0.9.5.134 read-only Evidence Budget decision.

    The budget manager does not skip work at runtime yet. It produces a stable
    decision report that can be used to move expensive Character ReOCR earlier
    in the pipeline without weakening DataGuard. Operational Truth is untouched.
    """
    try:
        rank = int(row.get("rank", 9999) or 9999)
    except Exception:
        rank = 9999
    try:
        alignment_score = float(row.get("alignment_score", 0.0) or 0.0)
    except Exception:
        alignment_score = 0.0
    try:
        power_similarity = float(row.get("power_similarity", 0.0) or 0.0)
    except Exception:
        power_similarity = 0.0
    fragment_confidence = float(evidence.get("evidence_avg_fragment_confidence", 0.0) or 0.0)
    display_coverage = float(evidence.get("display_coverage_score", 0.0) or 0.0)
    fragments = int(evidence.get("evidence_fragments_total", 0) or 0)
    unresolved = int(evidence.get("evidence_unresolved_fragments", 0) or 0)
    observed = int(evidence.get("evidence_observed_fragments", 0) or 0)
    gold_core = bool(row.get("gold_core_blocker", False))
    context_gap = bool(row.get("alignment_context_gap", False))

    if rank <= 10:
        ranking_weight = 1.0
    elif rank <= 25:
        ranking_weight = 0.82
    elif rank <= 50:
        ranking_weight = 0.65
    else:
        ranking_weight = 0.35

    coverage_potential = max(display_coverage, min(1.0, fragments / 6.0 if fragments else 0.0))
    risk_bonus = 0.12 if gold_core else 0.0
    context_penalty = 0.20 if context_gap else 0.0
    negative_evidence_penalty = min(0.30, (unresolved * 0.05) + (observed * 0.08))
    priority = (
        ranking_weight * 0.24
        + max(0.0, min(1.0, power_similarity)) * 0.15
        + max(0.0, min(1.0, alignment_score)) * 0.18
        + fragment_confidence * 0.18
        + coverage_potential * 0.17
        + risk_bonus
        - context_penalty
        - negative_evidence_penalty
    )
    priority = round(max(0.0, min(1.0, priority)), 4)

    decision = str(evidence.get("display_confidence_decision", "") or "")
    if context_gap:
        tier = "context_evidence_only"
        action = "contextual_suggestion_only"
        reason = "context_gap_read_only_no_budget_promotion"
    elif status in {"blocked_display_promotion", "alliance_reconstructed_name_blocked"} and (display_coverage < 0.50 or fragment_confidence < 0.72):
        tier = "low"
        action = "block_early_or_reuse_cache"
        reason = "promotion_guard_blocked_low_budget_return"
    elif decision == "eligible" and priority >= 0.70:
        tier = "high"
        action = "full_character_reocr_budget"
        reason = "high_priority_and_eligible_evidence"
    elif priority >= 0.62 and fragments > 0 and unresolved <= 1 and observed == 0:
        tier = "medium"
        action = "targeted_character_reocr_budget"
        reason = "recoverable_evidence_with_limited_open_targets"
    elif priority >= 0.50 and (fragment_confidence >= 0.70 or display_coverage >= 0.50):
        tier = "watch"
        action = "cache_or_limited_retry"
        reason = "some_evidence_but_not_enough_for_full_budget"
    else:
        tier = "low"
        action = "block_early_or_reuse_cache"
        reason = "low_coverage_or_low_fragment_confidence"

    expected_cost_ms = 0
    if action == "full_character_reocr_budget":
        expected_cost_ms = 12000
    elif action == "targeted_character_reocr_budget":
        expected_cost_ms = 6500
    elif action == "cache_or_limited_retry":
        expected_cost_ms = 2500
    else:
        expected_cost_ms = 0

    return {
        "evidence_priority_score": priority,
        "evidence_budget_tier": tier,
        "evidence_budget_action": action,
        "evidence_budget_reason": reason,
        "evidence_budget_expected_cost_ms": expected_cost_ms,
        "evidence_budget_operational_truth_modified": False,
    }

def _safe_char_replace(text: str, position: int, replacement: str) -> tuple[str, bool]:
    """Return text with one character replaced if the position is valid.

    Display Reconstruction is report-only. Failed replacements are surfaced in
    diagnostics instead of being guessed or forced into Operational Truth.
    """
    text = normalize_text(text)
    replacement = normalize_text(replacement)
    if not replacement:
        return text, False
    chars = list(text)
    if position < 0 or position >= len(chars):
        return text, False
    chars[position] = replacement[0]
    return "".join(chars), True


def _display_confidence_from_items(items: list[dict[str, Any]]) -> float:
    values: list[float] = []
    for item in items:
        try:
            values.append(float(item.get("confidence", 0.0) or 0.0))
        except Exception:
            continue
    if not values:
        return 0.0
    return round(sum(values) / max(len(values), 1), 4)


def _reconstruct_display_row(row: pd.Series) -> dict[str, Any]:
    """Build a read-only reconstructed display proposal from character evidence.

    v0.9.5.132: The engine consumes already-collected Character ReOCR evidence
    and produces guarded, report-only display proposals. It never changes expected/OCR
    fields, verified_* fields, exports, snapshots, or Ground Truth.  The goal is
    to make the Evidence Layer useful for Display Fidelity without weakening
    DataGuard.
    """
    expected_name = normalize_text(row.get("expected_name", ""))
    expected_tag = normalize_text(row.get("expected_alliance_display", row.get("expected_alliance", "")))
    observed_name = normalize_text(row.get("ocr_name", ""))
    observed_tag = normalize_text(row.get("ocr_alliance_display", row.get("ocr_alliance", "")))
    if not observed_name:
        observed_name = normalize_text(row.get("verified_name_display", ""))
    if not observed_tag:
        observed_tag = normalize_text(row.get("verified_alliance_display", ""))

    evidence_items = _parse_json_list(row.get("character_reocr_evidence", "[]"))
    read_only_items = _parse_json_list(row.get("read_only_reocr_evidence", "[]"))

    name = observed_name
    tag = observed_tag
    name_applied = 0
    tag_applied = 0
    unresolved = 0
    observed_votes = 0
    useful_items: list[dict[str, Any]] = []
    notes: list[str] = []

    for item in evidence_items:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status", "") or "")
        field = str(item.get("field", "") or "")
        expected_char = normalize_text(item.get("expected", ""))
        position = item.get("position", None)
        try:
            position_int = int(position)
        except Exception:
            position_int = -1
        if status == "verified_observed":
            observed_votes += 1
            useful_items.append(item)
            continue
        if status != "verified_expected":
            unresolved += 1
            continue
        if field == "player_name":
            name, applied = _safe_char_replace(name, position_int, expected_char)
            if applied:
                name_applied += 1
                useful_items.append(item)
            else:
                unresolved += 1
        elif field == "alliance_tag":
            tag, applied = _safe_char_replace(tag, position_int, expected_char)
            if applied:
                tag_applied += 1
                useful_items.append(item)
            else:
                unresolved += 1

    # v0.9.5.132 Display Reconstruction Guard:
    # Character evidence may propose display strings, but promotion is blocked
    # when the name base is UNKNOWN, evidence coverage is too thin, observed
    # votes contradict expected glyphs, or unresolved fragments remain. This is
    # report-only; Operational Truth is never modified.
    name_promotion_block_reasons: list[str] = []
    name_promotion_candidate = bool(name_applied)
    expected_name_len = len(expected_name) if expected_name else 0
    name_coverage = (name_applied / expected_name_len) if expected_name_len else 0.0
    if name_promotion_candidate:
        if observed_name.upper() == "UNKNOWN":
            name_promotion_block_reasons.append("blocked_unknown_base")
        if expected_name and name != expected_name and name_coverage < 0.5:
            name_promotion_block_reasons.append("blocked_low_coverage")
        if observed_votes:
            name_promotion_block_reasons.append("blocked_observed_votes")
        if unresolved:
            name_promotion_block_reasons.append("blocked_unresolved_fragments")

    if name_promotion_block_reasons:
        # Keep tag evidence, but do not surface a synthesized name built on an
        # unsafe base such as UNKNOWN -> GNKNIWN.
        name = observed_name
        notes.extend(name_promotion_block_reasons)

    display_promotion_eligible = not bool(name_promotion_block_reasons)
    display_promotion_block_reason = ";".join(dict.fromkeys(name_promotion_block_reasons))

    source = "none"
    status = "not_reconstructed"
    if name_applied or tag_applied:
        source = "character_reocr_evidence"
        status = "partial_reconstruction"
        if name_promotion_block_reasons and tag_applied and expected_tag and tag == expected_tag:
            status = "alliance_reconstructed_name_blocked"
        elif name_promotion_block_reasons:
            status = "blocked_display_promotion"
        elif expected_name and name == expected_name and expected_tag and tag == expected_tag:
            status = "full_display_reconstructed"
        elif expected_name and name == expected_name:
            status = "name_reconstructed"
        elif expected_tag and tag == expected_tag:
            status = "alliance_reconstructed"
    elif read_only_items:
        # Context-gap read-only suggestions are evidence-only. They are not
        # promoted to operational verified_display_* fields, but the display
        # reconstruction report should expose them as contextual proposals.
        first = read_only_items[0] if isinstance(read_only_items[0], dict) else {}
        suggested_name = normalize_text(first.get("suggested_name_display", ""))
        suggested_tag = normalize_text(first.get("suggested_alliance_display", ""))
        if suggested_name or suggested_tag:
            name = suggested_name or name
            tag = suggested_tag or tag
            source = "read_only_contextual_inference"
            status = "contextual_display_suggestion"
            display_promotion_eligible = False
            display_promotion_block_reason = "context_gap_evidence_only"
            notes.append("context_gap_evidence_only")
            useful_items.extend(read_only_items)

    if observed_votes:
        notes.append("observed_vote_blocks_expected_display")
    if unresolved:
        notes.append("unresolved_or_unapplied_fragments")
    if not (name_applied or tag_applied or read_only_items):
        if bool(row.get("verified_name_display_exact_match", False)) and bool(row.get("verified_alliance_display_exact_match", False)):
            status = "already_exact"
            source = "existing_verified_display"

    confidence = _display_confidence_from_items(useful_items)
    if source == "read_only_contextual_inference":
        try:
            confidence = round(float(row.get("read_only_confidence", 0.0) or row.get("inference_confidence", 0.0) or 0.0), 4)
        except Exception:
            confidence = 0.0
    elif status == "already_exact":
        confidence = 1.0

    evidence_confidence = _evidence_confidence_summary(
        useful_items,
        expected_name=expected_name,
        expected_tag=expected_tag,
        name_applied=name_applied,
        tag_applied=tag_applied,
        unresolved=unresolved,
        observed_votes=observed_votes,
        status=status,
    )
    # Promotion Guard 2.0: evidence confidence can only tighten promotion.
    # It never promotes context gaps or low-coverage fragments into Operational Truth.
    if evidence_confidence["display_confidence_decision"].startswith("blocked") and display_promotion_eligible:
        display_promotion_eligible = False
        display_promotion_block_reason = "blocked_evidence_confidence"
        notes.append("blocked_evidence_confidence")

    evidence_budget = _evidence_budget_decision(row, evidence_confidence, status)

    return {
        "display_reconstruction_status": status,
        "display_reconstruction_source": source,
        "display_reconstructed_name": name,
        "display_reconstructed_alliance_tag": tag,
        "display_reconstruction_confidence": confidence,
        "display_reconstruction_name_targets_applied": name_applied,
        "display_reconstruction_alliance_targets_applied": tag_applied,
        "display_reconstruction_unresolved_targets": unresolved,
        "display_reconstruction_observed_votes": observed_votes,
        "display_reconstruction_notes": ";".join(dict.fromkeys(notes)),
        "display_promotion_eligible": display_promotion_eligible,
        "display_promotion_block_reason": display_promotion_block_reason,
        **evidence_confidence,
        **evidence_budget,
        "display_reconstruction_operational_truth_modified": False,
    }


def _apply_display_reconstruction(detail: pd.DataFrame) -> pd.DataFrame:
    """Attach read-only display reconstruction columns to validation detail."""
    if detail.empty:
        return detail
    reconstructed = detail.apply(_reconstruct_display_row, axis=1, result_type="expand")
    return pd.concat([detail, reconstructed], axis=1)




def _is_latin_display_text(value: Any) -> bool:
    """Return True for display strings made of Latin letters, digits, spaces, and common accents/punctuation."""
    text = normalize_text(value)
    if not text or text.upper() == "UNKNOWN":
        return False
    for ch in text:
        if ch.isascii() and (ch.isalnum() or ch.isspace() or ch in "_-'.#"):
            continue
        # Latin-1 supplement accents used by player names such as Códy.
        if "\u00c0" <= ch <= "\u024f":
            continue
        return False
    return True


def _hamming_distance_same_length(left: str, right: str) -> int | None:
    left = normalize_text(left)
    right = normalize_text(right)
    if len(left) != len(right):
        return None
    return sum(1 for a, b in zip(left, right) if a != b)


def _gold_blocker_strike_i_clearance(row: pd.Series) -> tuple[bool, str]:
    """v0.9.5.141 Gold Regression & Strike II: clear one-glyph Latin blocker cases.

    This is deliberately narrow.  It only affects validator evidence status, never
    Operational Truth.  A row may be cleared when every non-name identity anchor is
    already proven and the remaining blocker is a single localized Latin glyph
    difference between expected display and observed/reconstructed display.
    """
    if not _bool_cell(row.get("gold_core_blocker", False)):
        return False, "not_a_gold_core_blocker"
    if _bool_cell(row.get("alignment_context_gap", False)):
        return False, "strike_blocked_context_gap_read_only"
    if not _bool_cell(row.get("power_match", False)):
        return False, "strike_blocked_power_not_proven"
    if not (_bool_cell(row.get("core_alliance_match", False)) or normalize_text(row.get("display_reconstructed_alliance_tag", "")) == normalize_text(row.get("expected_alliance_display", ""))):
        return False, "strike_blocked_core_alliance_not_proven"
    if not _bool_cell(row.get("display_promotion_eligible", False)):
        return False, "strike_blocked_promotion_not_eligible"
    if str(row.get("display_confidence_decision", "") or "").startswith("blocked"):
        return False, "strike_blocked_evidence_confidence"

    expected = normalize_text(row.get("expected_name", ""))
    reconstructed = normalize_text(row.get("display_reconstructed_name", "") or row.get("verified_name_display", "") or row.get("ocr_name", ""))
    if not (_is_latin_display_text(expected) and _is_latin_display_text(reconstructed)):
        return False, "strike_blocked_non_latin_or_unknown_name"
    distance = _hamming_distance_same_length(expected, reconstructed)
    if distance is None:
        return False, "strike_blocked_name_length_mismatch"
    if distance == 0:
        return True, "strike_exact_latin_display_already_proven"
    # Phase I intentionally clears only one localized glyph: high precision over recall.
    if distance == 1:
        return True, "strike_single_latin_glyph_difference_with_full_identity_anchors"
    return False, "strike_blocked_multiple_name_glyph_differences"



def _latin_compact(value: Any) -> str:
    """Compact Latin display text for guarded blocker-strike comparison."""
    text = normalize_text(value)
    return "".join(ch for ch in text if (ch.isascii() and ch.isalnum()) or ("\u00c0" <= ch <= "\u024f"))


def _levenshtein_ops(expected: str, observed: str) -> list[tuple[str, str, str, int, int]]:
    """Return a minimal edit script from observed to expected.

    Ops are tuples: (op, expected_char, observed_char, expected_index, observed_index)
    where op is equal/replace/insert/delete.  Insert means a character is missing
    in observed and should be inserted from expected; delete means observed has an
    extra character not present in expected.
    """
    a = normalize_text(expected)
    b = normalize_text(observed)
    n, m = len(a), len(b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,      # insert expected char
                dp[i][j - 1] + 1,      # delete observed char
                dp[i - 1][j - 1] + cost,
            )
    ops: list[tuple[str, str, str, int, int]] = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + (0 if a[i - 1] == b[j - 1] else 1):
            op = "equal" if a[i - 1] == b[j - 1] else "replace"
            ops.append((op, a[i - 1], b[j - 1], i - 1, j - 1))
            i -= 1
            j -= 1
        elif i > 0 and dp[i][j] == dp[i - 1][j] + 1:
            ops.append(("insert", a[i - 1], "", i - 1, j))
            i -= 1
        else:
            ops.append(("delete", "", b[j - 1], i, j - 1))
            j -= 1
    return list(reversed(ops))


_STRIKE_II_CONFUSION_FAMILIES = [
    set("2zZ"),
    set("1Il|"),
    set("0Oo"),
    set("5Ss"),
    set("8Bb"),
    set("6G"),
]


def _strike_ii_confusable(expected: str, observed: str) -> bool:
    if expected == observed:
        return True
    for family in _STRIKE_II_CONFUSION_FAMILIES:
        if expected in family and observed in family:
            return True
    return False


def _gold_blocker_strike_ii_clearance(row: pd.Series) -> tuple[bool, str]:
    """v0.9.5.141 Gold Blocker Strike II: clear one missing Latin glyph plus one confusable glyph.

    Strike I cleared single local substitutions.  Strike II remains narrow but
    handles the next safe class seen in the 551 benchmark: a fully anchored Latin
    display where the remaining difference is exactly one missing Latin character
    plus, optionally, one known local glyph confusion such as 2/Z or 1/l.

    This is evidence-only benchmark clearance. It never mutates snapshots,
    exports, Ground Truth, or Operational Truth.
    """
    if not _bool_cell(row.get("gold_core_blocker", False)):
        return False, "not_a_gold_core_blocker"
    if _bool_cell(row.get("alignment_context_gap", False)):
        return False, "strike_ii_blocked_context_gap_read_only"
    if not _bool_cell(row.get("power_match", False)):
        return False, "strike_ii_blocked_power_not_proven"
    if not (_bool_cell(row.get("core_alliance_match", False)) or normalize_text(row.get("display_reconstructed_alliance_tag", "")) == normalize_text(row.get("expected_alliance_display", ""))):
        return False, "strike_ii_blocked_core_alliance_not_proven"
    if _int_cell(row.get("display_reconstruction_observed_votes", 0)) > 0:
        return False, "strike_ii_blocked_observed_votes"
    if _int_cell(row.get("display_reconstruction_unresolved_targets", 0)) > 1:
        return False, "strike_ii_blocked_too_many_unresolved_fragments"

    expected = normalize_text(row.get("expected_name", ""))
    reconstructed = normalize_text(row.get("display_reconstructed_name", "") or row.get("verified_name_display", "") or row.get("ocr_name", ""))
    if not (_is_latin_display_text(expected) and _is_latin_display_text(reconstructed)):
        return False, "strike_ii_blocked_non_latin_or_unknown_name"
    expected_compact = _latin_compact(expected)
    reconstructed_compact = _latin_compact(reconstructed)
    if not expected_compact or not reconstructed_compact:
        return False, "strike_ii_blocked_empty_latin_core"

    ops = [op for op in _levenshtein_ops(expected_compact, reconstructed_compact) if op[0] != "equal"]
    if not ops:
        return True, "strike_ii_exact_latin_core_already_proven"
    if len(ops) > 2:
        return False, "strike_ii_blocked_more_than_two_latin_edits"

    inserts = [op for op in ops if op[0] == "insert"]
    deletes = [op for op in ops if op[0] == "delete"]
    replaces = [op for op in ops if op[0] == "replace"]
    if deletes:
        return False, "strike_ii_blocked_extra_observed_latin_glyph"
    if len(inserts) > 1 or len(replaces) > 1:
        return False, "strike_ii_blocked_edit_shape_not_supported"
    if replaces and not _strike_ii_confusable(replaces[0][1], replaces[0][2]):
        return False, "strike_ii_blocked_replacement_not_confusion_family"

    # Need at least one affirmative evidence signal. This prevents a pure string
    # similarity shortcut from clearing a blocker without Character Acquisition.
    confirmed = _int_cell(row.get("evidence_confirmed_fragments", 0)) + _int_cell(row.get("character_reocr_verified_expected", 0))
    if confirmed < 1:
        return False, "strike_ii_blocked_no_confirmed_character_evidence"

    return True, "strike_ii_one_missing_latin_glyph_plus_optional_confusable_with_full_identity_anchors"



def _gold_blocker_strike_iii_clearance(row: pd.Series) -> tuple[bool, str]:
    """v0.9.5.142 Gold Core Strike III: clear up to two confusion-only Latin substitutions.

    This gate is deliberately narrower than generic fuzzy matching. It requires
    current-snapshot identity anchors, zero unresolved/observed character votes,
    and confirmed character evidence for every changed position. It never
    mutates Operational Truth; it only clears the validator-side Gold Core flag.
    """
    if not _bool_cell(row.get("gold_core_blocker", False)):
        return False, "not_a_gold_core_blocker"
    if _bool_cell(row.get("alignment_context_gap", False)):
        return False, "strike_iii_blocked_context_gap_read_only"
    if _bool_cell(row.get("bad_match", False)) or str(row.get("match_method", "") or "") in {"missing", "blocked_rank_fallback"}:
        return False, "strike_iii_blocked_identity_match_not_accepted"
    if not _bool_cell(row.get("power_match", False)):
        return False, "strike_iii_blocked_power_not_proven"
    if not (_bool_cell(row.get("core_alliance_match", False)) or normalize_text(row.get("display_reconstructed_alliance_tag", "")) == normalize_text(row.get("expected_alliance_display", ""))):
        return False, "strike_iii_blocked_core_alliance_not_proven"
    if not _bool_cell(row.get("display_promotion_eligible", False)):
        return False, "strike_iii_blocked_promotion_guard"
    if _int_cell(row.get("display_reconstruction_observed_votes", 0)) > 0:
        return False, "strike_iii_blocked_observed_votes"
    if _int_cell(row.get("display_reconstruction_unresolved_targets", 0)) > 0:
        return False, "strike_iii_blocked_unresolved_fragments"

    expected = _latin_compact(normalize_text(row.get("expected_name", "")))
    reconstructed = _latin_compact(normalize_text(row.get("display_reconstructed_name", "") or row.get("verified_name_display", "") or row.get("ocr_name", "")))
    if not expected or not reconstructed or len(expected) != len(reconstructed):
        return False, "strike_iii_blocked_non_substitution_edit_shape"
    if not (_is_latin_display_text(expected) and _is_latin_display_text(reconstructed)):
        return False, "strike_iii_blocked_non_latin_name"

    ops = [op for op in _levenshtein_ops(expected, reconstructed) if op[0] != "equal"]
    if not ops:
        return True, "strike_iii_exact_latin_core_already_proven"
    if len(ops) > 2 or any(op[0] != "replace" for op in ops):
        return False, "strike_iii_blocked_requires_one_or_two_substitutions"
    if any(not _strike_ii_confusable(op[1], op[2]) for op in ops):
        return False, "strike_iii_blocked_substitution_not_confusion_family"

    confirmed = _int_cell(row.get("evidence_confirmed_fragments", 0)) + _int_cell(row.get("character_reocr_verified_expected", 0))
    if confirmed < len(ops):
        return False, "strike_iii_blocked_insufficient_confirmed_character_evidence"

    position_action = str(row.get("character_position_action", "") or "")
    if position_action in {"forced_position_acquisition", "position_adaptive_multicrop_retry"}:
        return False, "strike_iii_blocked_position_evidence_still_unstable"

    return True, "strike_iii_one_or_two_confusion_only_substitutions_with_full_identity_anchors"

def _gold_core_elimination_decision(row: pd.Series) -> dict[str, Any]:
    """Apply v0.9.5.142 Gold Core Strike III rules.

    This is the first functional blocker-elimination gate.  It does not mutate
    OCR export rows, snapshots, Ground Truth, or Operational Truth.  It only
    upgrades the validator's *evidence assessment* when a current-screenshot
    display reconstruction is strong enough to prove Core Identity.

    Guardrails:
    - context-gap inferences remain read-only and cannot clear blockers;
    - observed/unresolved evidence cannot clear blockers;
    - full display promotion must already be eligible;
    - name evidence must resolve the expected display name exactly;
    - alliance evidence must either resolve the expected display tag exactly or
      Core Alliance must already be proven by normalized same-snapshot evidence.
    """
    original_blocker = _bool_cell(row.get("gold_core_blocker", False))
    accepted = str(row.get("match_method", "") or "") not in {"missing", "blocked_rank_fallback"} and not _bool_cell(row.get("bad_match", False))
    context_gap = _bool_cell(row.get("alignment_context_gap", False))
    power_match = _bool_cell(row.get("power_match", False))
    promotion_eligible = _bool_cell(row.get("display_promotion_eligible", False))

    expected_name = normalize_text(row.get("expected_name", ""))
    expected_tag = normalize_text(row.get("expected_alliance_display", ""))
    reconstructed_name = normalize_text(row.get("display_reconstructed_name", ""))
    reconstructed_tag = normalize_text(row.get("display_reconstructed_alliance_tag", ""))

    name_exact = bool(expected_name and reconstructed_name == expected_name)
    tag_exact = bool((not expected_tag and not reconstructed_tag) or (expected_tag and reconstructed_tag == expected_tag))
    core_alliance = bool(tag_exact or _bool_cell(row.get("core_alliance_match", False)))
    unresolved = _int_cell(row.get("display_reconstruction_unresolved_targets", 0))
    observed_votes = _int_cell(row.get("display_reconstruction_observed_votes", 0))
    confidence_decision = str(row.get("display_confidence_decision", "") or "")
    reconstruction_status = str(row.get("display_reconstruction_status", "") or "")

    strict_clear = bool(
        original_blocker
        and accepted
        and not context_gap
        and power_match
        and promotion_eligible
        and name_exact
        and core_alliance
        and unresolved == 0
        and observed_votes == 0
        and not confidence_decision.startswith("blocked")
        and reconstruction_status in {"full_display_reconstructed", "name_reconstructed", "already_exact"}
    )
    strike_clear, strike_reason = _gold_blocker_strike_i_clearance(row)
    strike_ii_clear, strike_ii_reason = _gold_blocker_strike_ii_clearance(row)
    strike_iii_clear, strike_iii_reason = _gold_blocker_strike_iii_clearance(row)
    clear = bool(strict_clear or strike_clear or strike_ii_clear or strike_iii_clear)

    if strict_clear:
        reason = "display_reconstruction_proves_name_and_core_alliance"
        action = "clear_gold_core_blocker"
    elif strike_clear:
        reason = strike_reason
        action = "clear_gold_core_blocker_strike_i"
    elif strike_ii_clear:
        reason = strike_ii_reason
        action = "clear_gold_core_blocker_strike_ii"
    elif strike_iii_clear:
        reason = strike_iii_reason
        action = "clear_gold_core_blocker_strike_iii"
    elif not original_blocker:
        reason = "not_a_gold_core_blocker"
        action = "not_applicable"
    elif context_gap:
        reason = "blocked_context_gap_read_only"
        action = "keep_blocked"
    elif not promotion_eligible:
        reason = f"blocked_promotion_guard:{row.get('display_promotion_block_reason', '')}"
        action = "keep_blocked"
    elif not name_exact:
        reason = "blocked_name_not_reconstructed_to_expected"
        action = "keep_blocked"
    elif not core_alliance:
        reason = "blocked_core_alliance_not_proven"
        action = "keep_blocked"
    elif unresolved or observed_votes:
        reason = "blocked_unresolved_or_observed_character_evidence"
        action = "keep_blocked"
    else:
        reason = "blocked_guardrail_not_satisfied"
        action = "keep_blocked"

    return {
        "gold_core_elimination_candidate": bool(original_blocker),
        "gold_core_elimination_action": action,
        "gold_core_elimination_reason": reason,
        "gold_core_elimination_cleared": clear,
        "gold_core_blocker_before_elimination": original_blocker,
        "gold_core_blocker_after_elimination": bool(original_blocker and not clear),
        "gold_core_elimination_operational_truth_modified": False,
    }


def _apply_gold_core_elimination(detail: pd.DataFrame) -> pd.DataFrame:
    """Attach and apply v0.9.5.138 evidence-only Gold Core elimination.

    The validator's Core Identity metrics are allowed to use proven evidence;
    Operational Truth is not.  Cleared rows are marked as verified_core_identity
    for benchmark purposes only, with explicit elimination metadata preserved.
    """
    if detail.empty:
        return detail
    decisions = detail.apply(_gold_core_elimination_decision, axis=1, result_type="expand")
    out = pd.concat([detail, decisions], axis=1)
    cleared = out["gold_core_elimination_cleared"].fillna(False).astype(bool)
    if cleared.any():
        out.loc[cleared, "verified_core_identity_match"] = True
        out.loc[cleared, "verified_core_identity_resolution"] = True
        out.loc[cleared, "gold_core_blocker"] = False
        out.loc[cleared, "identity_policy_class"] = "gold_core_eliminated_display_reconstruction"
        # Preserve Full Gold strictness unless exact identity was already proven.
        out.loc[cleared, "identity_risk_reasons"] = out.loc[cleared, "identity_risk_reasons"].astype(str).apply(
            lambda value: ";".join(dict.fromkeys([part for part in (value + ";gold_core_eliminated_display_reconstruction").split(";") if part]))
        )
    return out


def _build_gold_core_elimination_report(detail: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build v0.9.5.142 Gold Core Strike III report."""
    cols = [
        "server", "rank", "expected_alliance_display", "ocr_alliance_display",
        "expected_name", "ocr_name", "verified_name_display", "verified_alliance_display",
        "display_reconstruction_status", "display_reconstructed_name", "display_reconstructed_alliance_tag",
        "display_promotion_eligible", "display_promotion_block_reason", "display_confidence_decision",
        "gold_core_blocker_before_elimination", "gold_core_blocker_after_elimination",
        "gold_core_elimination_candidate", "gold_core_elimination_action", "gold_core_elimination_reason",
        "gold_core_elimination_cleared", "verified_core_identity_match", "identity_policy_class",
        "power_match", "core_alliance_match", "alignment_context_gap", "gold_core_elimination_operational_truth_modified",
    ]
    if detail.empty:
        return pd.DataFrame([{
            "phase": "v0.9.5.141_character_position_intelligence",
            "rows": 0,
            "cleared_rows": 0,
            "remaining_blockers": 0,
            "operational_truth_modified": False,
        }]), pd.DataFrame(columns=cols)
    rows = detail.copy()
    for col in cols:
        if col not in rows.columns:
            rows[col] = ""
    report = rows[cols].copy()
    report = report[report["gold_core_elimination_candidate"].fillna(False).astype(bool) | report["gold_core_elimination_cleared"].fillna(False).astype(bool)].copy()
    if report.empty:
        return pd.DataFrame([{
            "phase": "v0.9.5.141_character_position_intelligence",
            "rows": 0,
            "cleared_rows": 0,
            "remaining_blockers": int(rows.get("gold_core_blocker", pd.Series(dtype=bool)).fillna(False).astype(bool).sum()),
            "operational_truth_modified": False,
        }]), report
    summary = report.groupby(["gold_core_elimination_action", "gold_core_elimination_reason"], dropna=False).agg(
        rows=("rank", "count"),
        cleared_rows=("gold_core_elimination_cleared", "sum"),
        remaining_blockers=("gold_core_blocker_after_elimination", "sum"),
        min_rank=("rank", "min"),
        max_rank=("rank", "max"),
    ).reset_index()
    summary.insert(0, "phase", "v0.9.5.141_character_position_intelligence")
    summary["operational_truth_modified"] = False
    return summary, report.sort_values(["gold_core_blocker_after_elimination", "rank"], ascending=[False, True]).reset_index(drop=True)

def _build_display_reconstruction_report(detail: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build v0.9.5.134 guarded Display Reconstruction + Evidence Budget report."""
    cols = [
        "server", "rank", "expected_alliance_display", "ocr_alliance_display",
        "expected_name", "ocr_name", "verified_name_display", "verified_alliance_display",
        "display_reconstruction_status", "display_reconstruction_source",
        "display_reconstructed_alliance_tag", "display_reconstructed_name",
        "display_reconstruction_confidence", "display_reconstruction_name_targets_applied",
        "display_reconstruction_alliance_targets_applied", "display_reconstruction_unresolved_targets",
        "display_reconstruction_observed_votes", "display_reconstruction_notes",
        "display_promotion_eligible", "display_promotion_block_reason",
        "evidence_fragments_total", "evidence_confirmed_fragments", "evidence_observed_fragments",
        "evidence_unresolved_fragments", "evidence_avg_fragment_confidence",
        "display_name_coverage_score", "display_alliance_coverage_score", "display_coverage_score",
        "display_confidence_decision", "evidence_priority_score", "evidence_budget_tier", "evidence_budget_action",
        "evidence_budget_reason", "evidence_avg_crop_quality", "evidence_avg_ocr_confidence",
        "evidence_avg_vote_consensus", "evidence_avg_position_stability", "evidence_avg_unicode_class",
        "alignment_context_gap", "gold_core_blocker", "row_integrity_status",
        "display_reconstruction_operational_truth_modified",
    ]
    if detail.empty:
        return pd.DataFrame(columns=["display_reconstruction_status", "rows"]), pd.DataFrame(columns=cols)
    rows = detail.copy()
    for col in cols:
        if col not in rows.columns:
            rows[col] = ""
    report = rows[cols].copy()
    report = report[report["display_reconstruction_status"].astype(str).ne("not_reconstructed")].copy()
    if report.empty:
        summary = pd.DataFrame([{
            "rows": 0,
            "reconstructed_rows": 0,
            "contextual_suggestion_rows": 0,
            "full_display_reconstructed_rows": 0,
            "already_exact_rows": 0,
            "operational_truth_modified": False,
        }])
        return summary, report
    summary = report.groupby(["display_reconstruction_status", "display_reconstruction_source"], dropna=False).agg(
        rows=("rank", "count"),
        avg_confidence=("display_reconstruction_confidence", "mean"),
        name_targets_applied=("display_reconstruction_name_targets_applied", "sum"),
        alliance_targets_applied=("display_reconstruction_alliance_targets_applied", "sum"),
        unresolved_targets=("display_reconstruction_unresolved_targets", "sum"),
        observed_votes=("display_reconstruction_observed_votes", "sum"),
        avg_fragment_confidence=("evidence_avg_fragment_confidence", "mean"),
        avg_display_coverage=("display_coverage_score", "mean"),
        promotion_eligible_rows=("display_promotion_eligible", "sum"),
        avg_priority_score=("evidence_priority_score", "mean"),
    ).reset_index()
    summary["avg_confidence"] = summary["avg_confidence"].astype(float).round(4)
    summary["avg_fragment_confidence"] = summary["avg_fragment_confidence"].astype(float).round(4)
    summary["avg_display_coverage"] = summary["avg_display_coverage"].astype(float).round(4)
    if "avg_priority_score" in summary.columns:
        summary["avg_priority_score"] = summary["avg_priority_score"].astype(float).round(4)
    summary.insert(0, "phase", "v0.9.5.141_character_position_intelligence")
    summary["operational_truth_modified"] = False
    return summary, report.sort_values(["rank", "display_reconstruction_status"]).reset_index(drop=True)


def _build_evidence_confidence_report(detail: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build v0.9.5.133 Evidence Confidence report.

    This report explains why a reconstructed display is eligible, suggested, or
    blocked. It is read-only and does not feed Operational Truth.
    """
    cols = [
        "server", "rank", "expected_alliance_display", "expected_name", "ocr_alliance_display", "ocr_name",
        "display_reconstruction_status", "display_reconstructed_alliance_tag", "display_reconstructed_name",
        "display_promotion_eligible", "display_promotion_block_reason", "display_confidence_decision",
        "evidence_priority_score", "evidence_budget_tier", "evidence_budget_action", "evidence_budget_reason",
        "evidence_fragments_total", "evidence_confirmed_fragments", "evidence_observed_fragments",
        "evidence_unresolved_fragments", "evidence_avg_fragment_confidence", "display_name_coverage_score",
        "display_alliance_coverage_score", "display_coverage_score", "evidence_avg_crop_quality",
        "evidence_avg_ocr_confidence", "evidence_avg_vote_consensus", "evidence_avg_position_stability",
        "evidence_avg_unicode_class", "alignment_context_gap", "gold_core_blocker",
        "display_reconstruction_operational_truth_modified",
    ]
    if detail.empty:
        return pd.DataFrame(columns=["display_confidence_decision", "rows"]), pd.DataFrame(columns=cols)
    rows = detail.copy()
    for col in cols:
        if col not in rows.columns:
            rows[col] = ""
    report = rows[cols].copy()
    report = report[report["display_reconstruction_status"].astype(str).ne("not_reconstructed")].copy()
    if report.empty:
        return pd.DataFrame([{"phase": "v0.9.5.141_character_position_intelligence", "rows": 0, "operational_truth_modified": False}]), report
    summary = report.groupby(["display_confidence_decision", "display_promotion_eligible"], dropna=False).agg(
        rows=("rank", "count"),
        avg_fragment_confidence=("evidence_avg_fragment_confidence", "mean"),
        avg_display_coverage=("display_coverage_score", "mean"),
        avg_name_coverage=("display_name_coverage_score", "mean"),
        avg_alliance_coverage=("display_alliance_coverage_score", "mean"),
        blocked_rows=("display_promotion_eligible", lambda values: int((~pd.Series(values).fillna(False).astype(bool)).sum())),
        context_gap_rows=("alignment_context_gap", lambda values: int(pd.Series(values).fillna(False).astype(bool).sum())),
        gold_core_blockers=("gold_core_blocker", lambda values: int(pd.Series(values).fillna(False).astype(bool).sum())),
    ).reset_index()
    for col in ["avg_fragment_confidence", "avg_display_coverage", "avg_name_coverage", "avg_alliance_coverage"]:
        summary[col] = pd.to_numeric(summary[col], errors="coerce").fillna(0).round(4)
    summary.insert(0, "phase", "v0.9.5.141_character_position_intelligence")
    summary["operational_truth_modified"] = False
    return summary, report.sort_values(["rank", "display_confidence_decision"]).reset_index(drop=True)


def _build_evidence_budget_report(detail: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build v0.9.5.134 Evidence Budget Manager report.

    The report ranks display-evidence rows by likely return on expensive ReOCR.
    It is deliberately read-only: it recommends budget allocation but does not
    mutate OCR output, exports, snapshots, Ground Truth, or Operational Truth.
    """
    cols = [
        "server", "rank", "expected_alliance_display", "expected_name", "ocr_alliance_display", "ocr_name",
        "display_reconstruction_status", "display_confidence_decision", "display_promotion_eligible",
        "evidence_priority_score", "evidence_budget_tier", "evidence_budget_action", "evidence_budget_reason",
        "evidence_budget_expected_cost_ms", "evidence_avg_fragment_confidence", "display_coverage_score",
        "display_name_coverage_score", "display_alliance_coverage_score", "evidence_fragments_total",
        "evidence_unresolved_fragments", "evidence_observed_fragments", "alignment_context_gap", "gold_core_blocker",
        "evidence_budget_operational_truth_modified",
    ]
    if detail.empty:
        return pd.DataFrame([{"phase": "v0.9.5.141_character_position_intelligence", "rows": 0, "operational_truth_modified": False}]), pd.DataFrame(columns=cols)
    rows = detail.copy()
    for col in cols:
        if col not in rows.columns:
            rows[col] = ""
    report = rows[cols].copy()
    report = report[report["display_reconstruction_status"].astype(str).ne("not_reconstructed")].copy()
    if report.empty:
        return pd.DataFrame([{"phase": "v0.9.5.141_character_position_intelligence", "rows": 0, "operational_truth_modified": False}]), report
    summary = report.groupby(["evidence_budget_tier", "evidence_budget_action"], dropna=False).agg(
        rows=("rank", "count"),
        avg_priority_score=("evidence_priority_score", "mean"),
        avg_fragment_confidence=("evidence_avg_fragment_confidence", "mean"),
        avg_display_coverage=("display_coverage_score", "mean"),
        expected_cost_ms=("evidence_budget_expected_cost_ms", "sum"),
        promotion_eligible_rows=("display_promotion_eligible", "sum"),
        context_gap_rows=("alignment_context_gap", lambda values: int(pd.Series(values).fillna(False).astype(bool).sum())),
        gold_core_blockers=("gold_core_blocker", lambda values: int(pd.Series(values).fillna(False).astype(bool).sum())),
    ).reset_index()
    for col in ["avg_priority_score", "avg_fragment_confidence", "avg_display_coverage"]:
        summary[col] = pd.to_numeric(summary[col], errors="coerce").fillna(0).round(4)
    summary.insert(0, "phase", "v0.9.5.141_character_position_intelligence")
    summary["operational_truth_modified"] = False
    return summary, report.sort_values(["evidence_priority_score", "rank"], ascending=[False, True]).reset_index(drop=True)



def _scheduler_priority_from_budget(row: pd.Series) -> dict[str, Any]:
    """Compute v0.9.5.136 Gold Accuracy Scheduler decision.

    In Gold Accuracy Mode the scheduler is an accuracy orchestrator, not a
    runtime saver. It may order work and label context-only rows, but it must
    not early-exit low budget rows merely to save time. Evidence collection is
    maximized; promotion and Operational Truth remain protected by the existing
    guards.
    """
    tier = str(row.get("evidence_budget_tier", "") or "").strip().lower()
    action = str(row.get("evidence_budget_action", "") or "").strip().lower()
    try:
        priority = float(row.get("evidence_priority_score", 0.0) or 0.0)
    except Exception:
        priority = 0.0
    try:
        cost_ms = int(float(row.get("evidence_budget_expected_cost_ms", 0) or 0))
    except Exception:
        cost_ms = 0
    try:
        coverage = float(row.get("display_coverage_score", 0.0) or 0.0)
    except Exception:
        coverage = 0.0
    try:
        frag_conf = float(row.get("evidence_avg_fragment_confidence", 0.0) or 0.0)
    except Exception:
        frag_conf = 0.0
    unresolved = int(float(row.get("evidence_unresolved_fragments", 0) or 0))
    observed = int(float(row.get("evidence_observed_fragments", 0) or 0))
    context_gap = bool(row.get("alignment_context_gap", False))
    promotion_eligible = bool(row.get("display_promotion_eligible", False))

    position_action = str(row.get("character_position_action", "") or "")
    try:
        position_risk = float(row.get("character_position_max_risk", 0.0) or 0.0)
    except Exception:
        position_risk = 0.0
    scheduled_cost_ms = cost_ms or 6500
    estimated_saved_ms = 0

    if (not context_gap) and position_action == "forced_position_acquisition":
        scheduler_priority = "critical"
        scheduler_decision = "schedule_position_forced_acquisition"
        scheduler_reason = "character_position_intelligence_critical_position_accuracy_first"
        queue_order = 5
        scheduled_cost_ms = max(cost_ms or 0, 15000)
    elif (not context_gap) and position_action == "position_adaptive_multicrop_retry":
        scheduler_priority = "high"
        scheduler_decision = "schedule_position_adaptive_multicrop_retry"
        scheduler_reason = "character_position_intelligence_weak_position_requires_extra_evidence"
        queue_order = 15
        scheduled_cost_ms = max(cost_ms or 0, 12000)
    elif context_gap or tier == "context_evidence_only":
        # Context-gap rows are evidence-only by DataGuard policy. They may carry
        # a contextual display suggestion, but they must not be promoted or
        # turned into Operational Truth.
        scheduler_priority = "evidence_only"
        scheduler_decision = "collect_context_evidence_only"
        scheduler_reason = "context_gap_read_only_evidence_operational_truth_locked"
        queue_order = 90
        scheduled_cost_ms = 0
    elif promotion_eligible and action == "full_character_reocr_budget" and priority >= 0.70:
        scheduler_priority = "critical" if priority >= 0.85 else "high"
        scheduler_decision = "schedule_full_reocr"
        scheduler_reason = "gold_accuracy_high_return_full_evidence"
        queue_order = 10 if scheduler_priority == "critical" else 20
        scheduled_cost_ms = cost_ms or 12000
    elif action == "full_character_reocr_budget" or tier == "high":
        scheduler_priority = "high"
        scheduler_decision = "schedule_full_reocr"
        scheduler_reason = "gold_accuracy_full_evidence_collection"
        queue_order = 20
        scheduled_cost_ms = cost_ms or 12000
    elif action == "targeted_character_reocr_budget" or tier == "medium":
        scheduler_priority = "medium"
        scheduler_decision = "schedule_targeted_reocr"
        scheduler_reason = "gold_accuracy_targeted_evidence_collection"
        queue_order = 30
        scheduled_cost_ms = cost_ms or 6500
    elif action == "cache_or_limited_retry" or tier == "watch":
        scheduler_priority = "watch"
        scheduler_decision = "schedule_limited_retry"
        scheduler_reason = "gold_accuracy_watchlist_retry_not_runtime_limited"
        queue_order = 50
        scheduled_cost_ms = cost_ms or 3500
    elif action == "block_early_or_reuse_cache" or tier == "low":
        scheduler_priority = "low"
        scheduler_decision = "schedule_accuracy_reocr"
        scheduler_reason = "gold_accuracy_mode_disables_runtime_early_exit"
        queue_order = 70
        scheduled_cost_ms = cost_ms or 6500
    else:
        scheduler_priority = "watch" if (frag_conf >= 0.50 or coverage >= 0.15 or unresolved > 0 or observed > 0) else "low"
        scheduler_decision = "schedule_accuracy_reocr"
        scheduler_reason = "gold_accuracy_default_collect_more_evidence"
        queue_order = 60 if scheduler_priority == "watch" else 70
        scheduled_cost_ms = cost_ms or 6500

    return {
        "evidence_scheduler_decision": scheduler_decision,
        "scheduler_priority": scheduler_priority,
        "scheduler_reason": scheduler_reason,
        "scheduler_queue_order": queue_order,
        "scheduler_expected_runtime_ms": scheduled_cost_ms,
        "scheduler_estimated_saved_ms": estimated_saved_ms,
        "scheduler_accuracy_mode": bool(GOLD_ACCURACY_MODE),
        "scheduler_active_phase": "v0.9.5.141_character_position_intelligence",
        "scheduler_operational_truth_modified": False,
    }


def _attach_evidence_scheduler(detail: pd.DataFrame) -> pd.DataFrame:
    """Attach v0.9.5.135 scheduler decisions to validation detail."""
    if detail.empty:
        return detail
    scheduled = detail.apply(_scheduler_priority_from_budget, axis=1, result_type="expand")
    return pd.concat([detail, scheduled], axis=1)


def _build_evidence_scheduler_report(detail: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build v0.9.5.136 Gold Accuracy Scheduler report.

    The scheduler report shows which Evidence Budget candidates should be
    executed under Gold Accuracy Mode. It is read-only for Operational Truth,
    but it intentionally disables runtime-first early exits in scheduling reports.
    """
    cols = [
        "server", "rank", "expected_alliance_display", "expected_name", "ocr_alliance_display", "ocr_name",
        "display_reconstruction_status", "display_confidence_decision", "display_promotion_eligible",
        "evidence_priority_score", "evidence_budget_tier", "evidence_budget_action", "evidence_budget_reason",
        "evidence_budget_expected_cost_ms", "evidence_scheduler_decision", "scheduler_priority",
        "scheduler_reason", "scheduler_queue_order", "scheduler_expected_runtime_ms", "scheduler_estimated_saved_ms",
        "evidence_avg_fragment_confidence", "display_coverage_score", "evidence_fragments_total",
        "evidence_unresolved_fragments", "evidence_observed_fragments", "alignment_context_gap", "gold_core_blocker",
        "scheduler_accuracy_mode", "scheduler_active_phase", "scheduler_operational_truth_modified",
    ]
    if detail.empty:
        return pd.DataFrame([{"phase": "v0.9.5.141_character_position_intelligence", "rows": 0, "operational_truth_modified": False}]), pd.DataFrame(columns=cols)
    rows = detail.copy()
    for col in cols:
        if col not in rows.columns:
            rows[col] = ""
    report = rows[cols].copy()
    report = report[report["display_reconstruction_status"].astype(str).ne("not_reconstructed")].copy()
    if report.empty:
        return pd.DataFrame([{"phase": "v0.9.5.141_character_position_intelligence", "rows": 0, "operational_truth_modified": False}]), report
    summary = report.groupby(["scheduler_priority", "evidence_scheduler_decision"], dropna=False).agg(
        rows=("rank", "count"),
        avg_priority_score=("evidence_priority_score", "mean"),
        scheduled_runtime_ms=("scheduler_expected_runtime_ms", "sum"),
        estimated_saved_ms=("scheduler_estimated_saved_ms", "sum"),
        budget_expected_cost_ms=("evidence_budget_expected_cost_ms", "sum"),
        promotion_eligible_rows=("display_promotion_eligible", "sum"),
        context_gap_rows=("alignment_context_gap", lambda values: int(pd.Series(values).fillna(False).astype(bool).sum())),
        gold_core_blockers=("gold_core_blocker", lambda values: int(pd.Series(values).fillna(False).astype(bool).sum())),
    ).reset_index()
    summary["avg_priority_score"] = pd.to_numeric(summary["avg_priority_score"], errors="coerce").fillna(0).round(4)
    summary.insert(0, "phase", "v0.9.5.141_character_position_intelligence")
    summary["operational_truth_modified"] = False
    return summary, report.sort_values(["scheduler_queue_order", "evidence_priority_score", "rank"], ascending=[True, False, True]).reset_index(drop=True)


def _acquisition_vote_consensus(row: pd.Series) -> tuple[str, float, int]:
    """Return a lightweight consensus signal from Character ReOCR debug votes.

    v0.9.5.137 Character Acquisition Engine Phase I converts raw targeted
    Character ReOCR fragments into observation-level consensus.  This is still
    evidence-only: it never mutates OCR rows, Ground Truth, snapshots, exports,
    verified display fields, or Operational Truth.
    """
    selected = normalize_text(row.get("selected", ""))
    nonempty = normalize_text(row.get("nonempty_vote_chars", ""))
    votes: list[str] = []
    if nonempty:
        votes.extend([v for v in nonempty.split(";") if v])
    if selected:
        votes.append(selected)
    if not votes:
        return selected, 0.0, 0
    counts: dict[str, int] = {}
    for vote in votes:
        counts[vote] = counts.get(vote, 0) + 1
    winner, count = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0]
    consensus = count / max(len(votes), 1)
    return winner, round(consensus, 4), len(votes)


def _acquisition_crop_quality(row: pd.Series) -> float:
    diagnostic = str(row.get("debug_read", row.get("crop_diagnostic", "")) or "")
    anchor = str(row.get("crop_anchor_status", "") or "")
    width = float(row.get("crop_width", 0) or 0)
    height = float(row.get("crop_height", 0) or 0)
    quality = 0.70
    if diagnostic == "verified_expected":
        quality += 0.15
    if diagnostic == "vote_outside_allowed_set":
        quality -= 0.12
    if diagnostic == "crop_field_mismatch" or anchor == "field_mismatch":
        quality -= 0.20
    if anchor == "anchor_seen":
        quality += 0.10
    if anchor == "cache_hit":
        quality += 0.12
    if width >= 16 and height >= 40:
        quality += 0.05
    return round(max(0.0, min(1.0, quality)), 4)


def _character_observation_confidence(row: pd.Series) -> float:
    try:
        base_conf = float(row.get("confidence", 0.0) or 0.0)
    except Exception:
        base_conf = 0.0
    _, vote_consensus, _ = _acquisition_vote_consensus(row)
    crop_quality = _acquisition_crop_quality(row)
    status = str(row.get("target_status", "") or "")
    status_weight = {
        "verified_expected": 1.0,
        "verified_observed": 0.78,
        "ambiguous_vote": 0.45,
        "unresolved": 0.25,
    }.get(status, 0.35)
    # Confidence is deliberately bounded and explainable rather than magical.
    confidence = (base_conf * 0.38) + (vote_consensus * 0.27) + (crop_quality * 0.20) + (status_weight * 0.15)
    return round(max(0.0, min(1.0, confidence)), 4)


def _build_character_acquisition_report(detail: pd.DataFrame, character_reocr_debug: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build v0.9.5.137 Character Acquisition Engine reports.

    The report groups multiple targeted observations per character position,
    computes consensus, confidence, crop quality, and a position heatmap.  It is
    an Evidence Layer artifact only.  Promotion remains controlled by the
    Display Reconstruction/Promotion Guard and Operational Truth is locked.
    """
    if character_reocr_debug.empty:
        summary = pd.DataFrame([{
            "phase": "v0.9.5.141_character_position_intelligence",
            "rows": 0,
            "observations": 0,
            "avg_observation_confidence": 0.0,
            "operational_truth_modified": False,
        }])
        empty_cols = [
            "server", "rank", "target_field", "target_position", "observation_count",
            "consensus_char", "consensus_status", "consensus_confidence",
            "vote_consensus", "crop_quality_avg", "expected_char", "observed_char",
            "selected_chars", "target_statuses", "debug_reads", "character_acquisition_operational_truth_modified",
        ]
        return summary, pd.DataFrame(columns=empty_cols), pd.DataFrame(columns=empty_cols), detail

    obs = character_reocr_debug.copy()
    obs["acquisition_consensus_char"] = ""
    obs["acquisition_vote_consensus"] = 0.0
    obs["acquisition_vote_count"] = 0
    for idx, row in obs.iterrows():
        char, vote_consensus, vote_count = _acquisition_vote_consensus(row)
        obs.at[idx, "acquisition_consensus_char"] = char
        obs.at[idx, "acquisition_vote_consensus"] = vote_consensus
        obs.at[idx, "acquisition_vote_count"] = vote_count
    obs["acquisition_crop_quality"] = obs.apply(_acquisition_crop_quality, axis=1)
    obs["acquisition_observation_confidence"] = obs.apply(_character_observation_confidence, axis=1)
    obs["character_acquisition_operational_truth_modified"] = False

    group_cols = ["server", "rank", "target_field", "target_position"]
    records: list[dict[str, Any]] = []
    for keys, group in obs.groupby(group_cols, dropna=False):
        server, rank, field, position = keys
        selected_chars = [normalize_text(v) for v in group.get("acquisition_consensus_char", pd.Series(dtype=str)).tolist() if normalize_text(v)]
        counts: dict[str, int] = {}
        for char in selected_chars:
            counts[char] = counts.get(char, 0) + 1
        consensus_char = ""
        consensus_ratio = 0.0
        if counts:
            consensus_char, count = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0]
            consensus_ratio = count / max(sum(counts.values()), 1)
        statuses = sorted(set(str(v or "") for v in group.get("target_status", pd.Series(dtype=str)).tolist()))
        debug_reads = sorted(set(str(v or "") for v in group.get("debug_read", pd.Series(dtype=str)).tolist()))
        expected_chars = [normalize_text(v) for v in group.get("target_expected", pd.Series(dtype=str)).tolist() if normalize_text(v)]
        observed_chars = [normalize_text(v) for v in group.get("target_observed", pd.Series(dtype=str)).tolist() if normalize_text(v)]
        expected_char = expected_chars[0] if expected_chars else ""
        observed_char = observed_chars[0] if observed_chars else ""
        avg_conf = float(pd.to_numeric(group["acquisition_observation_confidence"], errors="coerce").fillna(0).mean())
        avg_vote = float(pd.to_numeric(group["acquisition_vote_consensus"], errors="coerce").fillna(0).mean())
        avg_crop = float(pd.to_numeric(group["acquisition_crop_quality"], errors="coerce").fillna(0).mean())
        if "verified_expected" in statuses and consensus_char == expected_char and avg_conf >= 0.70:
            consensus_status = "consensus_verified_expected"
        elif "verified_observed" in statuses and consensus_char == observed_char and avg_conf >= 0.70:
            consensus_status = "consensus_verified_observed"
        elif avg_conf >= 0.62 and consensus_ratio >= 0.66 and consensus_char:
            consensus_status = "consensus_probable"
        elif "ambiguous_vote" in statuses:
            consensus_status = "consensus_ambiguous"
        else:
            consensus_status = "consensus_unresolved"
        records.append({
            "server": server,
            "rank": rank,
            "target_field": field,
            "target_position": position,
            "observation_count": int(len(group)),
            "consensus_char": consensus_char,
            "consensus_status": consensus_status,
            "consensus_confidence": round(avg_conf, 4),
            "vote_consensus": round(avg_vote, 4),
            "crop_quality_avg": round(avg_crop, 4),
            "expected_char": expected_char,
            "observed_char": observed_char,
            "selected_chars": ";".join(selected_chars),
            "target_statuses": ";".join(statuses),
            "debug_reads": ";".join(debug_reads),
            "character_acquisition_operational_truth_modified": False,
        })

    consensus = pd.DataFrame(records)
    if consensus.empty:
        heatmap = pd.DataFrame(columns=["target_field", "target_position", "positions", "avg_consensus_confidence", "verified_positions", "problem_positions"])
    else:
        heatmap = consensus.groupby(["target_field", "target_position"], dropna=False).agg(
            positions=("rank", "count"),
            avg_consensus_confidence=("consensus_confidence", "mean"),
            avg_vote_consensus=("vote_consensus", "mean"),
            avg_crop_quality=("crop_quality_avg", "mean"),
            avg_observation_count=("observation_count", "mean"),
            verified_positions=("consensus_status", lambda values: int(pd.Series(values).astype(str).str.contains("verified_expected|verified_observed", regex=True).sum())),
            probable_positions=("consensus_status", lambda values: int(pd.Series(values).astype(str).eq("consensus_probable").sum())),
            ambiguous_positions=("consensus_status", lambda values: int(pd.Series(values).astype(str).eq("consensus_ambiguous").sum())),
            unresolved_positions=("consensus_status", lambda values: int(pd.Series(values).astype(str).eq("consensus_unresolved").sum())),
        ).reset_index()
        for col in ["avg_consensus_confidence", "avg_vote_consensus", "avg_crop_quality", "avg_observation_count"]:
            heatmap[col] = pd.to_numeric(heatmap[col], errors="coerce").fillna(0).round(4)
        heatmap["problem_positions"] = heatmap["ambiguous_positions"] + heatmap["unresolved_positions"]

    if consensus.empty:
        summary = pd.DataFrame([{
            "phase": "v0.9.5.141_character_position_intelligence",
            "rows": 0,
            "observations": int(len(obs)),
            "avg_observation_confidence": round(float(obs["acquisition_observation_confidence"].mean()), 4) if len(obs) else 0.0,
            "operational_truth_modified": False,
        }])
    else:
        summary = consensus.groupby(["target_field", "consensus_status"], dropna=False).agg(
            rows=("rank", "count"),
            observations=("observation_count", "sum"),
            avg_consensus_confidence=("consensus_confidence", "mean"),
            avg_vote_consensus=("vote_consensus", "mean"),
            avg_crop_quality=("crop_quality_avg", "mean"),
        ).reset_index()
        summary.insert(0, "phase", "v0.9.5.141_character_position_intelligence")
        for col in ["avg_consensus_confidence", "avg_vote_consensus", "avg_crop_quality"]:
            summary[col] = pd.to_numeric(summary[col], errors="coerce").fillna(0).round(4)
        summary["operational_truth_modified"] = False

    detail_out = detail.copy()
    if not consensus.empty:
        by_rank = consensus.groupby(["server", "rank"], dropna=False).agg(
            character_acquisition_positions=("target_position", "count"),
            character_acquisition_verified_positions=("consensus_status", lambda values: int(pd.Series(values).astype(str).str.contains("verified_expected|verified_observed", regex=True).sum())),
            character_acquisition_probable_positions=("consensus_status", lambda values: int(pd.Series(values).astype(str).eq("consensus_probable").sum())),
            character_acquisition_unresolved_positions=("consensus_status", lambda values: int(pd.Series(values).astype(str).eq("consensus_unresolved").sum())),
            character_acquisition_avg_confidence=("consensus_confidence", "mean"),
        ).reset_index()
        by_rank["character_acquisition_avg_confidence"] = pd.to_numeric(by_rank["character_acquisition_avg_confidence"], errors="coerce").fillna(0).round(4)
        detail_out = detail_out.merge(by_rank, on=["server", "rank"], how="left")
    for col in [
        "character_acquisition_positions", "character_acquisition_verified_positions",
        "character_acquisition_probable_positions", "character_acquisition_unresolved_positions",
        "character_acquisition_avg_confidence",
    ]:
        if col not in detail_out.columns:
            detail_out[col] = 0
        detail_out[col] = pd.to_numeric(detail_out[col], errors="coerce").fillna(0)
    detail_out["character_acquisition_operational_truth_modified"] = False
    return summary, consensus, heatmap, detail_out


def _position_intelligence_level(risk_score: float) -> str:
    if risk_score >= 0.70:
        return "critical"
    if risk_score >= 0.50:
        return "weak"
    if risk_score >= 0.30:
        return "watch"
    return "stable"


def _position_intelligence_action(level: str, problem_positions: int, avg_confidence: float) -> str:
    if level == "critical":
        return "forced_position_acquisition"
    if level == "weak":
        return "position_adaptive_multicrop_retry"
    if level == "watch" or problem_positions > 0 or avg_confidence < 0.70:
        return "watch_position_collect_extra_evidence"
    return "standard_acquisition"


def _build_character_position_intelligence_report(
    acquisition_rows: pd.DataFrame,
    acquisition_heatmap: pd.DataFrame,
    detail: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build v0.9.5.141 Character Position Intelligence reports.

    This layer turns Character Acquisition heatmap data into actionable,
    position-specific intelligence. It does not mutate OCR output, Ground Truth,
    exports, snapshots, or Operational Truth. Its functional output is consumed
    by the Evidence Scheduler as an accuracy-first hint: weak positions are
    scheduled for stronger evidence collection instead of being treated like an
    entire bad name.
    """
    empty_position_cols = [
        "phase", "target_field", "target_position", "positions", "verified_positions",
        "probable_positions", "ambiguous_positions", "unresolved_positions", "problem_positions",
        "problem_ratio", "avg_consensus_confidence", "avg_vote_consensus", "avg_crop_quality",
        "avg_observation_count", "position_risk_score", "position_intelligence_level",
        "position_intelligence_action", "position_intelligence_reason",
        "character_position_operational_truth_modified",
    ]
    empty_row_cols = [
        "server", "rank", "expected_name", "ocr_name", "expected_alliance_display", "ocr_alliance_display",
        "character_position_max_risk", "character_position_critical_positions", "character_position_weak_positions",
        "character_position_watch_positions", "character_position_action", "character_position_reason",
        "character_position_focus", "character_position_operational_truth_modified",
    ]
    if acquisition_heatmap.empty:
        summary = pd.DataFrame([{
            "phase": "v0.9.5.141_character_position_intelligence",
            "positions": 0,
            "critical_positions": 0,
            "weak_positions": 0,
            "watch_positions": 0,
            "stable_positions": 0,
            "operational_truth_modified": False,
        }])
        return summary, pd.DataFrame(columns=empty_position_cols), pd.DataFrame(columns=empty_row_cols), detail

    positions = acquisition_heatmap.copy()
    for col in ["positions", "verified_positions", "probable_positions", "ambiguous_positions", "unresolved_positions", "problem_positions"]:
        if col not in positions.columns:
            positions[col] = 0
        positions[col] = pd.to_numeric(positions[col], errors="coerce").fillna(0)
    for col in ["avg_consensus_confidence", "avg_vote_consensus", "avg_crop_quality"]:
        if col not in positions.columns:
            positions[col] = 0.0
        positions[col] = pd.to_numeric(positions[col], errors="coerce").fillna(0.0)
    if "avg_observation_count" not in positions.columns:
        positions["avg_observation_count"] = 1.0
    positions["avg_observation_count"] = pd.to_numeric(positions["avg_observation_count"], errors="coerce").fillna(1.0)
    positions["problem_ratio"] = (positions["problem_positions"] / positions["positions"].replace(0, 1)).round(4)
    # Risk is deliberately explainable: unresolved/ambiguous positions, weak confidence,
    # weak crop quality, and single-observation evidence are all bad for Gold Accuracy.
    positions["position_risk_score"] = (
        (positions["problem_ratio"] * 0.35)
        + ((1 - positions["avg_consensus_confidence"].clip(0, 1)) * 0.30)
        + ((1 - positions["avg_crop_quality"].clip(0, 1)) * 0.20)
        + ((positions["avg_observation_count"].le(1).astype(float)) * 0.15)
    ).clip(0, 1).round(4)
    positions["position_intelligence_level"] = positions["position_risk_score"].apply(_position_intelligence_level)
    positions["position_intelligence_action"] = positions.apply(
        lambda r: _position_intelligence_action(
            str(r.get("position_intelligence_level", "stable")),
            int(r.get("problem_positions", 0) or 0),
            float(r.get("avg_consensus_confidence", 0.0) or 0.0),
        ),
        axis=1,
    )
    positions["position_intelligence_reason"] = positions.apply(
        lambda r: ";".join(filter(None, [
            "low_consensus_confidence" if float(r.get("avg_consensus_confidence", 0) or 0) < 0.70 else "",
            "problem_positions_present" if int(r.get("problem_positions", 0) or 0) > 0 else "",
            "weak_crop_quality" if float(r.get("avg_crop_quality", 0) or 0) < 0.70 else "",
            "single_observation_only" if float(r.get("avg_observation_count", 1) or 1) <= 1 else "",
        ])) or "position_stable",
        axis=1,
    )
    positions.insert(0, "phase", "v0.9.5.141_character_position_intelligence")
    positions["character_position_operational_truth_modified"] = False

    summary = positions.groupby(["target_field", "position_intelligence_level", "position_intelligence_action"], dropna=False).agg(
        positions=("target_position", "count"),
        avg_position_risk=("position_risk_score", "mean"),
        avg_consensus_confidence=("avg_consensus_confidence", "mean"),
        problem_positions=("problem_positions", "sum"),
    ).reset_index()
    summary.insert(0, "phase", "v0.9.5.141_character_position_intelligence")
    for col in ["avg_position_risk", "avg_consensus_confidence"]:
        summary[col] = pd.to_numeric(summary[col], errors="coerce").fillna(0).round(4)
    summary["operational_truth_modified"] = False

    detail_out = detail.copy()
    if acquisition_rows.empty:
        row_actions = pd.DataFrame(columns=empty_row_cols)
    else:
        join_cols = ["target_field", "target_position", "position_risk_score", "position_intelligence_level", "position_intelligence_action", "position_intelligence_reason"]
        rows = acquisition_rows.merge(positions[join_cols], on=["target_field", "target_position"], how="left")
        rows["position_risk_score"] = pd.to_numeric(rows["position_risk_score"], errors="coerce").fillna(0.0)
        def _row_action(group: pd.DataFrame) -> pd.Series:
            levels = group.get("position_intelligence_level", pd.Series(dtype=str)).astype(str).tolist()
            actions = group.get("position_intelligence_action", pd.Series(dtype=str)).astype(str).tolist()
            risks = pd.to_numeric(group.get("position_risk_score", pd.Series(dtype=float)), errors="coerce").fillna(0.0)
            focus = []
            for _, gr in group.sort_values("position_risk_score", ascending=False).head(5).iterrows():
                focus.append(f"{gr.get('target_field')}[{gr.get('target_position')}]:{gr.get('position_intelligence_level')}:{float(gr.get('position_risk_score') or 0):.2f}")
            if "critical" in levels:
                action = "forced_position_acquisition"
            elif "weak" in levels:
                action = "position_adaptive_multicrop_retry"
            elif "watch" in levels:
                action = "watch_position_collect_extra_evidence"
            else:
                action = "standard_acquisition"
            return pd.Series({
                "character_position_max_risk": round(float(risks.max() if len(risks) else 0.0), 4),
                "character_position_critical_positions": int(levels.count("critical")),
                "character_position_weak_positions": int(levels.count("weak")),
                "character_position_watch_positions": int(levels.count("watch")),
                "character_position_action": action,
                "character_position_reason": ";".join(sorted(set(a for a in actions if a))) or "standard_acquisition",
                "character_position_focus": " | ".join(focus),
                "character_position_operational_truth_modified": False,
            })
        row_actions = rows.groupby(["server", "rank"], dropna=False).apply(_row_action, include_groups=False).reset_index()
        keep = ["server", "rank", "expected_name", "ocr_name", "expected_alliance_display", "ocr_alliance_display"]
        base = detail[[c for c in keep if c in detail.columns]].copy()
        row_actions = row_actions.merge(base, on=["server", "rank"], how="left")
        ordered = [c for c in empty_row_cols if c in row_actions.columns]
        row_actions = row_actions[ordered]
        detail_out = detail_out.merge(row_actions[[c for c in row_actions.columns if c in ["server", "rank"] or c.startswith("character_position_")]], on=["server", "rank"], how="left")

    for col, default in {
        "character_position_max_risk": 0.0,
        "character_position_critical_positions": 0,
        "character_position_weak_positions": 0,
        "character_position_watch_positions": 0,
        "character_position_action": "standard_acquisition",
        "character_position_reason": "standard_acquisition",
        "character_position_focus": "",
        "character_position_operational_truth_modified": False,
    }.items():
        if col not in detail_out.columns:
            detail_out[col] = default
        else:
            detail_out[col] = detail_out[col].fillna(default)
    return summary, positions, row_actions, detail_out

def _build_ocr_evidence_report(detail: pd.DataFrame, character_reocr_debug: pd.DataFrame) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
    """Build row/fragment provenance diagnostics for OCR evidence inspection."""
    evidence_rows: list[dict[str, Any]] = []
    fragment_rows: list[dict[str, Any]] = []
    for _, row in detail.iterrows():
        rank = row.get("rank")
        server = row.get("server")
        row_debug = pd.DataFrame()
        if not character_reocr_debug.empty:
            row_debug = character_reocr_debug[
                (character_reocr_debug.get("server") == server)
                & (character_reocr_debug.get("rank") == rank)
            ].copy()
        status, reason = _row_evidence_status(row, row_debug)
        target_count = int(len(row_debug)) if not row_debug.empty else 0
        unresolved_targets = int((row_debug.get("target_status", pd.Series(dtype=str)).astype(str) == "unresolved").sum()) if not row_debug.empty else 0
        verified_expected_targets = int((row_debug.get("target_status", pd.Series(dtype=str)).astype(str) == "verified_expected").sum()) if not row_debug.empty else 0
        verified_observed_targets = int((row_debug.get("target_status", pd.Series(dtype=str)).astype(str) == "verified_observed").sum()) if not row_debug.empty else 0
        field_mismatch_targets = int((row_debug.get("crop_anchor_status", pd.Series(dtype=str)).astype(str) == "field_mismatch").sum()) if not row_debug.empty else 0
        vote_outside_targets = int((row_debug.get("crop_diagnostic", pd.Series(dtype=str)).astype(str) == "vote_outside_allowed_set").sum()) if not row_debug.empty else 0
        evidence_rows.append({
            "server": server,
            "rank": rank,
            "ocr_rank": row.get("ocr_rank"),
            "screenshot": row.get("ground_truth_screenshot"),
            "ocr_source_file": row.get("ocr_source_file"),
            "ocr_sheet": row.get("ocr_sheet"),
            "row_slot": row.get("ground_truth_row_slot"),
            "row_integrity_status": status,
            "row_integrity_reason": reason,
            "alignment_guard_status": row.get("alignment_guard_status"),
            "alignment_safe_for_character_verification": row.get("alignment_safe_for_character_verification"),
            "alignment_context_gap": row.get("alignment_context_gap"),
            "match_method": row.get("match_method"),
            "failure_class": row.get("failure_class"),
            "expected_name": row.get("expected_name"),
            "ocr_name": row.get("ocr_name"),
            "verified_name_display": row.get("verified_name_display"),
            "expected_name_latin_core": row.get("expected_name_latin_core"),
            "ocr_name_latin_core": row.get("ocr_name_latin_core"),
            "expected_alliance_display": row.get("expected_alliance_display"),
            "ocr_alliance_display": row.get("ocr_alliance_display"),
            "verified_alliance_display": row.get("verified_alliance_display"),
            "expected_power": row.get("expected_power"),
            "ocr_power": row.get("ocr_power"),
            "power_match": row.get("power_match"),
            "rank_match": row.get("rank_match"),
            "verified_core_identity_match": row.get("verified_core_identity_match"),
            "gold_core_blocker": row.get("gold_core_blocker"),
            "character_reocr_targets": row.get("character_reocr_targets"),
            "character_reocr_verified_expected": row.get("character_reocr_verified_expected"),
            "character_reocr_verified_observed": row.get("character_reocr_verified_observed"),
            "character_reocr_unresolved": row.get("character_reocr_unresolved"),
            "evidence_fragment_rows": target_count,
            "evidence_verified_expected_targets": verified_expected_targets,
            "evidence_verified_observed_targets": verified_observed_targets,
            "evidence_unresolved_targets": unresolved_targets,
            "evidence_field_mismatch_targets": field_mismatch_targets,
            "evidence_vote_outside_allowed_targets": vote_outside_targets,
            "source_evidence_note": "derived_from_validator_detail_and_character_reocr_debug",
        })
        if not row_debug.empty:
            for _, frag in row_debug.iterrows():
                fragment_rows.append({
                    "server": server,
                    "rank": rank,
                    "screenshot": frag.get("screenshot") or row.get("ground_truth_screenshot"),
                    "row_slot": frag.get("row_slot"),
                    "target_index": frag.get("target_index"),
                    "target_field": frag.get("target_field"),
                    "target_position": frag.get("target_position"),
                    "target_expected": frag.get("target_expected"),
                    "target_observed": frag.get("target_observed"),
                    "target_status": frag.get("target_status"),
                    "selected": frag.get("selected"),
                    "confidence": frag.get("confidence"),
                    "crop_box": frag.get("crop_box"),
                    "crop_strategy": frag.get("crop_strategy"),
                    "crop_anchor_status": frag.get("crop_anchor_status"),
                    "crop_anchor_text": frag.get("crop_anchor_text"),
                    "crop_diagnostic": frag.get("crop_diagnostic"),
                    "vote_texts": frag.get("vote_texts"),
                    "nonempty_vote_chars": frag.get("nonempty_vote_chars"),
                    "debug_read": frag.get("debug_read"),
                    "target_total_ms": frag.get("target_total_ms"),
                    "ocr_read_ms": frag.get("ocr_read_ms"),
                    "provenance": "character_reocr_target",
                })
    evidence_df = pd.DataFrame(evidence_rows)
    fragments_df = pd.DataFrame(fragment_rows)
    if not evidence_df.empty:
        total_rows = int(len(evidence_df))
        ok_mask = evidence_df["row_integrity_status"].astype(str).isin({"ROW_OK_NO_REOCR", "ROW_OK_WITH_REOCR", "ROW_OK_POLICY_BUDGET", "ROW_OK_POLICY_NONLOCAL", "ROW_OK_WITH_CROP_WARNING", "ROW_OK_WITH_VOTE_WARNING", "ROW_VOTE_OUTSIDE_ALLOWED_SET"})
        inspect_mask = ~ok_mask
        status_summary = evidence_df.groupby("row_integrity_status", dropna=False).agg(
            rows=("rank", "count"),
            core_blockers=("gold_core_blocker", lambda values: int(pd.Series(values).fillna(False).astype(bool).sum())),
            context_gaps=("alignment_context_gap", lambda values: int(pd.Series(values).fillna(False).astype(bool).sum())),
            unresolved_targets=("evidence_unresolved_targets", "sum"),
            field_mismatch_targets=("evidence_field_mismatch_targets", "sum"),
        ).reset_index().to_dict(orient="records")
    else:
        total_rows = 0
        ok_mask = pd.Series(dtype=bool)
        inspect_mask = pd.Series(dtype=bool)
        status_summary = []
    payload = {
        "summary": {
            "rows": total_rows,
            "row_integrity_ok_rows": int(ok_mask.sum()) if len(evidence_df) else 0,
            "row_integrity_review_rows": int(inspect_mask.sum()) if len(evidence_df) else 0,
            "row_integrity_score": round((float(ok_mask.sum()) / max(total_rows, 1)) * 100.0, 2) if total_rows else 0.0,
            "fragment_rows": int(len(fragments_df)),
            "source": "ground_truth_validator_detail_and_character_reocr_debug",
            "operational_truth_modified": False,
        },
        "status_summary": status_summary,
        "rows": evidence_df.to_dict(orient="records"),
        "fragments": fragments_df.to_dict(orient="records"),
    }
    return payload, evidence_df, fragments_df

def write_report(summary: ValidationSummary, detail: pd.DataFrame, category: pd.DataFrame, output_dir: Path, runtime_metrics: dict[str, float] | None = None) -> None:
    report_write_start = time.perf_counter()
    runtime_metrics = dict(runtime_metrics or {})
    output_dir.mkdir(parents=True, exist_ok=True)
    # Backward-compatible report generation for older smoke tests and legacy
    # report DataFrames that predate v0.9.5.111 verified-display columns.
    default_columns = {
        "verified_name_display_exact_match": detail.get("name_display_exact_match", pd.Series(False, index=detail.index)),
        "verified_alliance_display_exact_match": detail.get("alliance_display_exact_match", pd.Series(False, index=detail.index)),
        "verified_exact_identity_match": detail.get("exact_identity_match", pd.Series(False, index=detail.index)),
        "verified_identity_resolution": pd.Series(False, index=detail.index),
        "verified_core_identity_match": detail.get("verified_exact_identity_match", detail.get("exact_identity_match", pd.Series(False, index=detail.index))),
        "verified_core_identity_resolution": pd.Series(False, index=detail.index),
        "gold_core_blocker": detail.get("gold_fidelity_blocker", pd.Series(False, index=detail.index)),
        "script_limited_core_identity_match": pd.Series(False, index=detail.index),
        "script_limited_core_identity_resolution": pd.Series(False, index=detail.index),
        "script_limited_policy_reason": pd.Series("", index=detail.index),
        "latin_residual_core_identity_match": pd.Series(False, index=detail.index),
        "latin_residual_core_identity_resolution": pd.Series(False, index=detail.index),
        "latin_residual_policy_reason": pd.Series("", index=detail.index),
        "identity_policy_class": pd.Series("full_display_required", index=detail.index),
        "verified_name_display": detail.get("ocr_name", pd.Series("", index=detail.index)),
        "verified_alliance_display": detail.get("ocr_alliance_display", pd.Series("", index=detail.index)),
    }
    for col, values in default_columns.items():
        if col not in detail.columns:
            detail[col] = values
    summary_rows = [asdict(summary)]
    failures = detail[
        (detail["match_method"] == "missing")
        | (detail["bad_match"])
        | (~detail["name_exact_match"])
        | (~detail["alliance_match"])
        | (~detail["power_match"])
        | (detail["identity_risk"])
    ].copy()

    failure_summary = detail.groupby("failure_class", dropna=False).agg(
        rows=("rank", "count"),
        power_matches=("power_match", "sum"),
        alliance_matches=("alliance_match", "sum"),
        usable_identity_matches=("usable_identity_match", "sum"),
        player_name_display_exact_matches=("name_display_exact_match", "sum"),
        alliance_tag_display_exact_matches=("alliance_display_exact_match", "sum"),
        exact_identity_matches=("exact_identity_match", "sum"),
        verified_exact_identity_matches=("verified_exact_identity_match", "sum"),
        verified_identity_resolution_rows=("verified_identity_resolution", "sum"),
        verified_core_identity_matches=("verified_core_identity_match", "sum"),
        verified_core_identity_resolution_rows=("verified_core_identity_resolution", "sum"),
        script_limited_core_identity_matches=("script_limited_core_identity_match", "sum"),
        script_limited_core_identity_resolution_rows=("script_limited_core_identity_resolution", "sum"),
        latin_residual_core_identity_matches=("latin_residual_core_identity_match", "sum"),
        latin_residual_core_identity_resolution_rows=("latin_residual_core_identity_resolution", "sum"),
        gold_core_blocker_rows=("gold_core_blocker", "sum"),
        identity_risk_rows=("identity_risk", "sum"),
        character_verification_candidate_rows=("character_verification_candidate", "sum"),
        high_value_character_verification_rows=("high_value_character_verification", "sum"),
        gold_fidelity_blocker_rows=("gold_fidelity_blocker", "sum"),
        character_reocr_targets=("character_reocr_targets", "sum"),
        character_reocr_verified_expected=("character_reocr_verified_expected", "sum"),
        character_reocr_skipped_nonlocal=("character_reocr_skipped_nonlocal", "sum"),
    ).reset_index()

    json_path = output_dir / "ground_truth_validation_report.json"
    identity_risk_detail = detail[detail["identity_risk"]].copy()
    identity_risk_summary = identity_risk_detail.groupby("identity_risk_reasons", dropna=False).agg(
        rows=("rank", "count"),
        high_value_rows=("high_value_identity_risk", "sum"),
        usable_identity_matches=("usable_identity_match", "sum"),
        exact_identity_matches=("exact_identity_match", "sum"),
        verified_exact_identity_matches=("verified_exact_identity_match", "sum"),
        verified_identity_resolution_rows=("verified_identity_resolution", "sum"),
        verified_core_identity_matches=("verified_core_identity_match", "sum"),
        verified_core_identity_resolution_rows=("verified_core_identity_resolution", "sum"),
        script_limited_core_identity_matches=("script_limited_core_identity_match", "sum"),
        script_limited_core_identity_resolution_rows=("script_limited_core_identity_resolution", "sum"),
        latin_residual_core_identity_matches=("latin_residual_core_identity_match", "sum"),
        latin_residual_core_identity_resolution_rows=("latin_residual_core_identity_resolution", "sum"),
        gold_core_blocker_rows=("gold_core_blocker", "sum"),
    ).reset_index() if not identity_risk_detail.empty else pd.DataFrame(columns=["identity_risk_reasons", "rows", "high_value_rows", "usable_identity_matches", "exact_identity_matches", "verified_exact_identity_matches", "verified_identity_resolution_rows", "verified_core_identity_matches", "verified_core_identity_resolution_rows", "gold_core_blocker_rows"])

    gold_fidelity_blockers = detail[detail.get("gold_fidelity_blocker", pd.Series(dtype=bool))].copy()
    gold_blocker_triage, gold_blocker_triage_summary = _build_gold_blocker_triage(gold_fidelity_blockers)
    core_identity_detail = detail[detail.get("verified_core_identity_match", pd.Series(False, index=detail.index))].copy()
    core_identity_summary = pd.DataFrame([{
        "rows": int(len(detail)),
        "verified_core_identity_matches": int(detail.get("verified_core_identity_match", pd.Series(dtype=bool)).sum()),
        "verified_core_identity_resolution_rows": int(detail.get("verified_core_identity_resolution", pd.Series(dtype=bool)).sum()),
        "script_limited_core_identity_matches": int(detail.get("script_limited_core_identity_match", pd.Series(dtype=bool)).sum()),
        "script_limited_core_identity_resolution_rows": int(detail.get("script_limited_core_identity_resolution", pd.Series(dtype=bool)).sum()),
        "latin_residual_core_identity_matches": int(detail.get("latin_residual_core_identity_match", pd.Series(dtype=bool)).sum()),
        "latin_residual_core_identity_resolution_rows": int(detail.get("latin_residual_core_identity_resolution", pd.Series(dtype=bool)).sum()),
        "gold_core_blocker_rows": int(detail.get("gold_core_blocker", pd.Series(dtype=bool)).sum()),
        "rank_only_full_gold_blockers": int((detail.get("verified_core_identity_match", pd.Series(False, index=detail.index)) & ~detail.get("verified_exact_identity_match", pd.Series(False, index=detail.index))).sum()),
    }])
    script_limited_policy_detail = detail[detail.get("script_limited_core_identity_match", pd.Series(False, index=detail.index))].copy()
    script_limited_policy_summary = script_limited_policy_detail.groupby("script_limited_policy_reason", dropna=False).agg(
        rows=("rank", "count"),
        high_value_rows=("high_value_identity_risk", "sum"),
        verified_core_identity_matches=("verified_core_identity_match", "sum"),
        gold_core_blocker_rows=("gold_core_blocker", "sum"),
        avg_name_normalized_similarity=("name_normalized_similarity", "mean"),
    ).reset_index() if not script_limited_policy_detail.empty else pd.DataFrame(columns=["script_limited_policy_reason", "rows", "high_value_rows", "verified_core_identity_matches", "gold_core_blocker_rows", "avg_name_normalized_similarity"])
    if not script_limited_policy_summary.empty and "avg_name_normalized_similarity" in script_limited_policy_summary.columns:
        script_limited_policy_summary["avg_name_normalized_similarity"] = pd.to_numeric(script_limited_policy_summary["avg_name_normalized_similarity"], errors="coerce").round(4)
    latin_residual_policy_detail = detail[detail.get("latin_residual_core_identity_match", pd.Series(False, index=detail.index))].copy()
    latin_residual_policy_summary = latin_residual_policy_detail.groupby("latin_residual_policy_reason", dropna=False).agg(
        rows=("rank", "count"),
        high_value_rows=("high_value_identity_risk", "sum"),
        verified_core_identity_matches=("verified_core_identity_match", "sum"),
        gold_core_blocker_rows=("gold_core_blocker", "sum"),
        avg_name_normalized_similarity=("name_normalized_similarity", "mean"),
    ).reset_index() if not latin_residual_policy_detail.empty else pd.DataFrame(columns=["latin_residual_policy_reason", "rows", "high_value_rows", "verified_core_identity_matches", "gold_core_blocker_rows", "avg_name_normalized_similarity"])
    if not latin_residual_policy_summary.empty and "avg_name_normalized_similarity" in latin_residual_policy_summary.columns:
        latin_residual_policy_summary["avg_name_normalized_similarity"] = pd.to_numeric(latin_residual_policy_summary["avg_name_normalized_similarity"], errors="coerce").round(4)

    alignment_context_gaps = detail[detail.get("alignment_context_gap", pd.Series(dtype=bool))].copy()
    alignment_guard_summary = alignment_context_gaps.groupby("alignment_guard_status", dropna=False).agg(
        rows=("rank", "count"),
        inference_rows=("match_method", lambda values: int(values.astype(str).str.startswith("inference_").sum())),
        character_reocr_targets=("character_reocr_targets", "sum"),
        gold_fidelity_blocker_rows=("gold_fidelity_blocker", "sum"),
    ).reset_index() if not alignment_context_gaps.empty else pd.DataFrame(columns=["alignment_guard_status", "rows", "inference_rows", "character_reocr_targets", "gold_fidelity_blocker_rows"])

    alignment_intelligence_rows = detail[[
        col for col in [
            "server", "rank", "ocr_rank", "expected_name", "ocr_name", "expected_alliance_display",
            "ocr_alliance_display", "expected_power", "ocr_power", "match_method", "failure_class",
            "alignment_guard_status", "alignment_context_gap", "alignment_score",
            "alignment_score_evidence", "verification_allowed_read_only", "verification_block_reason",
            "read_only_verification_status", "read_only_reocr_executed", "read_only_reocr_evidence",
            "read_only_suggested_display", "read_only_confidence", "read_only_operational_truth_modified",
            "inference_status", "inference_confidence", "inference_evidence", "gap_status", "gap_reason",
            "gap_previous_anchor_rank", "gap_next_anchor_rank", "operational_truth_modified"
        ] if col in detail.columns
    ]].copy()
    alignment_intelligence_summary = pd.DataFrame([{
        "rows": int(len(detail)),
        "context_gap_rows": int(detail.get("alignment_context_gap", pd.Series(False, index=detail.index)).fillna(False).astype(bool).sum()),
        "read_only_verification_candidate_rows": int(detail.get("verification_allowed_read_only", pd.Series(False, index=detail.index)).fillna(False).astype(bool).sum()),
        "read_only_reocr_executed_rows": int(detail.get("read_only_reocr_executed", pd.Series(False, index=detail.index)).fillna(False).astype(bool).sum()),
        "avg_read_only_confidence": round(float(pd.to_numeric(detail.get("read_only_confidence", pd.Series(dtype=float)), errors="coerce").fillna(0).mean()), 4) if len(detail) else 0.0,
        "avg_alignment_score": round(float(pd.to_numeric(detail.get("alignment_score", pd.Series(dtype=float)), errors="coerce").fillna(0).mean()), 4) if len(detail) else 0.0,
        "max_alignment_score": round(float(pd.to_numeric(detail.get("alignment_score", pd.Series(dtype=float)), errors="coerce").fillna(0).max()), 4) if len(detail) else 0.0,
        "operational_truth_modified": False,
        "phase": "v0.9.5.141_character_position_intelligence",
    }])
    character_verification_detail = detail[detail["character_verification_candidate"]].copy()
    character_verification_summary = character_verification_detail.groupby("character_verification_reasons", dropna=False).agg(
        rows=("rank", "count"),
        high_value_rows=("high_value_character_verification", "sum"),
        exact_identity_matches=("exact_identity_match", "sum"),
        verified_exact_identity_matches=("verified_exact_identity_match", "sum"),
        verified_identity_resolution_rows=("verified_identity_resolution", "sum"),
        verified_core_identity_matches=("verified_core_identity_match", "sum"),
        verified_core_identity_resolution_rows=("verified_core_identity_resolution", "sum"),
        script_limited_core_identity_matches=("script_limited_core_identity_match", "sum"),
        script_limited_core_identity_resolution_rows=("script_limited_core_identity_resolution", "sum"),
        latin_residual_core_identity_matches=("latin_residual_core_identity_match", "sum"),
        latin_residual_core_identity_resolution_rows=("latin_residual_core_identity_resolution", "sum"),
        gold_core_blocker_rows=("gold_core_blocker", "sum"),
    ).reset_index() if not character_verification_detail.empty else pd.DataFrame(columns=["character_verification_reasons", "rows", "high_value_rows", "exact_identity_matches", "verified_exact_identity_matches", "verified_identity_resolution_rows", "verified_core_identity_matches", "verified_core_identity_resolution_rows", "gold_core_blocker_rows"])
    character_reocr_debug = _flatten_character_reocr_debug(detail)
    if not character_reocr_debug.empty:
        character_reocr_debug_summary = character_reocr_debug.groupby(["target_field", "target_status", "debug_read"], dropna=False).agg(
            rows=("rank", "count"),
            high_value_rows=("rank", lambda values: int(pd.to_numeric(values, errors="coerce").le(10).sum())),
            avg_vote_count=("vote_count", "mean"),
        ).reset_index()
        character_reocr_debug_summary["avg_vote_count"] = character_reocr_debug_summary["avg_vote_count"].round(2)
    else:
        character_reocr_debug_summary = pd.DataFrame(columns=["target_field", "target_status", "debug_read", "rows", "high_value_rows", "avg_vote_count"])

    character_acquisition_summary, character_acquisition_rows, character_acquisition_heatmap, detail = _build_character_acquisition_report(detail, character_reocr_debug)
    character_position_summary, character_position_rows, character_position_rank_rows, detail = _build_character_position_intelligence_report(character_acquisition_rows, character_acquisition_heatmap, detail)
    ocr_evidence_payload, ocr_evidence_rows, ocr_evidence_fragments = _build_ocr_evidence_report(detail, character_reocr_debug)
    detail = _attach_evidence_scheduler(detail)
    display_reconstruction_summary, display_reconstruction_rows = _build_display_reconstruction_report(detail)
    evidence_confidence_summary, evidence_confidence_rows = _build_evidence_confidence_report(detail)
    evidence_budget_summary, evidence_budget_rows = _build_evidence_budget_report(detail)
    evidence_scheduler_summary, evidence_scheduler_rows = _build_evidence_scheduler_report(detail)
    gold_core_elimination_summary, gold_core_elimination_rows = _build_gold_core_elimination_report(detail)
    gold_core_blocker_report, gold_core_blocker_summary = _build_gold_core_blocker_report(gold_blocker_triage, ocr_evidence_rows)
    gold_core_resolution_plan, gold_core_resolution_summary = _build_gold_core_resolution_plan_report(gold_core_blocker_report)

    json_payload = {
        "summary": summary_rows[0],
        "category_summary": category.to_dict(orient="records"),
        "failure_summary": failure_summary.to_dict(orient="records"),
        "identity_risk_summary": identity_risk_summary.to_dict(orient="records"),
        "identity_risks": identity_risk_detail.to_dict(orient="records"),
        "character_verification_summary": character_verification_summary.to_dict(orient="records"),
        "character_verification_candidates": character_verification_detail.to_dict(orient="records"),
        "gold_fidelity_blockers": gold_fidelity_blockers.to_dict(orient="records"),
        "gold_blocker_triage_summary": gold_blocker_triage_summary.to_dict(orient="records"),
        "gold_blocker_triage": gold_blocker_triage.to_dict(orient="records"),
        "gold_core_blocker_summary": gold_core_blocker_summary.to_dict(orient="records"),
        "gold_core_blockers": gold_core_blocker_report.to_dict(orient="records"),
        "gold_core_resolution_summary": gold_core_resolution_summary.to_dict(orient="records"),
        "gold_core_resolution_plan": gold_core_resolution_plan.to_dict(orient="records"),
        "gold_core_elimination_summary": gold_core_elimination_summary.to_dict(orient="records"),
        "gold_core_elimination_rows": gold_core_elimination_rows.to_dict(orient="records"),
        "core_identity_summary": core_identity_summary.to_dict(orient="records"),
        "script_limited_policy_summary": script_limited_policy_summary.to_dict(orient="records"),
        "script_limited_policy_rows": script_limited_policy_detail.to_dict(orient="records"),
        "latin_residual_policy_summary": latin_residual_policy_summary.to_dict(orient="records"),
        "latin_residual_policy_rows": latin_residual_policy_detail.to_dict(orient="records"),
        "core_identity_verified_rows": core_identity_detail.to_dict(orient="records"),
        "alignment_guard_summary": alignment_guard_summary.to_dict(orient="records"),
        "alignment_context_gaps": alignment_context_gaps.to_dict(orient="records"),
        "alignment_intelligence_summary": alignment_intelligence_summary.to_dict(orient="records"),
        "alignment_intelligence_rows": alignment_intelligence_rows.to_dict(orient="records"),
        "character_reocr": {
            "target_count": int(detail.get("character_reocr_targets", pd.Series(dtype=int)).sum()),
            "verified_expected": int(detail.get("character_reocr_verified_expected", pd.Series(dtype=int)).sum()),
            "verified_display_resolutions": int(detail.get("verified_identity_resolution", pd.Series(dtype=bool)).sum()),
            "verified_core_identity_resolutions": int(detail.get("verified_core_identity_resolution", pd.Series(dtype=bool)).sum()),
            "verified_observed": int(detail.get("character_reocr_verified_observed", pd.Series(dtype=int)).sum()),
            "unresolved": int(detail.get("character_reocr_unresolved", pd.Series(dtype=int)).sum()),
            "skipped_nonlocal": int(detail.get("character_reocr_skipped_nonlocal", pd.Series(dtype=int)).sum()),
            "debug_rows": int(len(character_reocr_debug)),
        },
        "character_reocr_debug_summary": character_reocr_debug_summary.to_dict(orient="records"),
        "character_reocr_debug": character_reocr_debug.to_dict(orient="records"),
        "character_acquisition_summary": character_acquisition_summary.to_dict(orient="records"),
        "character_acquisition_rows": character_acquisition_rows.to_dict(orient="records"),
        "character_acquisition_heatmap": character_acquisition_heatmap.to_dict(orient="records"),
        "character_position_summary": character_position_summary.to_dict(orient="records"),
        "character_position_rows": character_position_rows.to_dict(orient="records"),
        "character_position_rank_rows": character_position_rank_rows.to_dict(orient="records"),
        "ocr_evidence_summary": ocr_evidence_payload.get("summary", {}),
        "ocr_evidence_status_summary": ocr_evidence_payload.get("status_summary", []),
        "ocr_evidence_rows": ocr_evidence_rows.to_dict(orient="records"),
        "ocr_evidence_fragments": ocr_evidence_fragments.to_dict(orient="records"),
        "evidence_confidence_summary": evidence_confidence_summary.to_dict(orient="records"),
        "evidence_confidence_rows": evidence_confidence_rows.to_dict(orient="records"),
        "evidence_budget_summary": evidence_budget_summary.to_dict(orient="records"),
        "evidence_budget_rows": evidence_budget_rows.to_dict(orient="records"),
        "evidence_scheduler_summary": evidence_scheduler_summary.to_dict(orient="records"),
        "evidence_scheduler_rows": evidence_scheduler_rows.to_dict(orient="records"),
        "details": detail.to_dict(orient="records"),
    }
    json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    reocr_debug_json_path = output_dir / "character_reocr_debug_report.json"
    reocr_debug_json_path.write_text(json.dumps({"summary": character_reocr_debug_summary.to_dict(orient="records"), "details": character_reocr_debug.to_dict(orient="records")}, ensure_ascii=False, indent=2), encoding="utf-8")
    character_acquisition_json_path = output_dir / "character_acquisition_report.json"
    character_acquisition_json_path.write_text(json.dumps(_json_safe({"summary": character_acquisition_summary.to_dict(orient="records"), "details": character_acquisition_rows.to_dict(orient="records"), "heatmap": character_acquisition_heatmap.to_dict(orient="records")}), ensure_ascii=False, indent=2), encoding="utf-8")
    character_position_json_path = output_dir / "character_position_intelligence_report.json"
    character_position_json_path.write_text(json.dumps(_json_safe({"summary": character_position_summary.to_dict(orient="records"), "positions": character_position_rows.to_dict(orient="records"), "rank_actions": character_position_rank_rows.to_dict(orient="records")}), ensure_ascii=False, indent=2), encoding="utf-8")
    ocr_evidence_json_path = output_dir / "ocr_evidence_report.json"
    ocr_evidence_json_path.write_text(json.dumps(_json_safe(ocr_evidence_payload), ensure_ascii=False, indent=2), encoding="utf-8")
    gold_core_json_path = output_dir / "gold_core_blocker_report.json"
    gold_core_json_path.write_text(json.dumps(_json_safe({"summary": gold_core_blocker_summary.to_dict(orient="records"), "details": gold_core_blocker_report.to_dict(orient="records")}), ensure_ascii=False, indent=2), encoding="utf-8")
    gold_core_resolution_json_path = output_dir / "gold_core_resolution_plan_report.json"
    gold_core_resolution_json_path.write_text(json.dumps(_json_safe({"summary": gold_core_resolution_summary.to_dict(orient="records"), "details": gold_core_resolution_plan.to_dict(orient="records")}), ensure_ascii=False, indent=2), encoding="utf-8")
    gold_core_elimination_json_path = output_dir / "gold_core_elimination_report.json"
    gold_core_elimination_json_path.write_text(json.dumps(_json_safe({"summary": gold_core_elimination_summary.to_dict(orient="records"), "details": gold_core_elimination_rows.to_dict(orient="records")}), ensure_ascii=False, indent=2), encoding="utf-8")
    alignment_intelligence_json_path = output_dir / "alignment_intelligence_report.json"
    alignment_intelligence_json_path.write_text(json.dumps(_json_safe({"summary": alignment_intelligence_summary.to_dict(orient="records"), "details": alignment_intelligence_rows.to_dict(orient="records")}), ensure_ascii=False, indent=2), encoding="utf-8")
    display_reconstruction_json_path = output_dir / "display_reconstruction_report.json"
    display_reconstruction_json_path.write_text(json.dumps(_json_safe({"summary": display_reconstruction_summary.to_dict(orient="records"), "details": display_reconstruction_rows.to_dict(orient="records")}), ensure_ascii=False, indent=2), encoding="utf-8")
    evidence_confidence_json_path = output_dir / "evidence_confidence_report.json"
    evidence_confidence_json_path.write_text(json.dumps(_json_safe({"summary": evidence_confidence_summary.to_dict(orient="records"), "details": evidence_confidence_rows.to_dict(orient="records")}), ensure_ascii=False, indent=2), encoding="utf-8")
    evidence_budget_json_path = output_dir / "evidence_budget_report.json"
    evidence_budget_json_path.write_text(json.dumps(_json_safe({"summary": evidence_budget_summary.to_dict(orient="records"), "details": evidence_budget_rows.to_dict(orient="records")}), ensure_ascii=False, indent=2), encoding="utf-8")
    evidence_scheduler_json_path = output_dir / "evidence_scheduler_report.json"
    evidence_scheduler_json_path.write_text(json.dumps(_json_safe({"summary": evidence_scheduler_summary.to_dict(orient="records"), "details": evidence_scheduler_rows.to_dict(orient="records")}), ensure_ascii=False, indent=2), encoding="utf-8")

    inference_detail = detail[detail["match_method"].astype(str).str.startswith("inference_")].copy()
    inference_summary = {
        "inference_rows": int(len(inference_detail)),
        "accepted": int((inference_detail.get("inference_status", "") == "accepted").sum()) if not inference_detail.empty else 0,
        "avg_confidence": round(float(inference_detail["inference_confidence"].mean()), 4) if not inference_detail.empty and "inference_confidence" in inference_detail else 0.0,
        "read_only": True,
        "operational_truth_modified": False,
    }
    inference_json_path = output_dir / "inference_report.json"
    inference_json_path.write_text(json.dumps({"summary": inference_summary, "details": inference_detail.to_dict(orient="records")}, ensure_ascii=False, indent=2), encoding="utf-8")

    xlsx_path = output_dir / "ground_truth_validation_report.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        pd.DataFrame(summary_rows).to_excel(writer, sheet_name="summary", index=False)
        _sanitize_frame(category).to_excel(writer, sheet_name="category_summary", index=False)
        _sanitize_frame(failure_summary).to_excel(writer, sheet_name="failure_summary", index=False)
        _sanitize_frame(identity_risk_summary).to_excel(writer, sheet_name="identity_risk_summary", index=False)
        _sanitize_frame(identity_risk_detail).to_excel(writer, sheet_name="identity_risks", index=False)
        _sanitize_frame(character_verification_summary).to_excel(writer, sheet_name="char_verify_summary", index=False)
        _sanitize_frame(character_verification_detail).to_excel(writer, sheet_name="char_verify_candidates", index=False)
        _sanitize_frame(gold_fidelity_blockers).to_excel(writer, sheet_name="gold_fidelity_blockers", index=False)
        _sanitize_frame(gold_blocker_triage_summary).to_excel(writer, sheet_name="gold_blocker_triage", index=False)
        _sanitize_frame(gold_blocker_triage).to_excel(writer, sheet_name="gold_blocker_details", index=False)
        _sanitize_frame(gold_core_blocker_summary).to_excel(writer, sheet_name="gold_core_summary", index=False)
        _sanitize_frame(gold_core_blocker_report).to_excel(writer, sheet_name="gold_core_blockers", index=False)
        _sanitize_frame(gold_core_resolution_summary).to_excel(writer, sheet_name="gold_core_plan", index=False)
        _sanitize_frame(gold_core_resolution_plan).to_excel(writer, sheet_name="gold_core_plan_rows", index=False)
        _sanitize_frame(gold_core_elimination_summary).to_excel(writer, sheet_name="gold_core_elim", index=False)
        _sanitize_frame(gold_core_elimination_rows).to_excel(writer, sheet_name="gold_core_elim_rows", index=False)
        _sanitize_frame(core_identity_summary).to_excel(writer, sheet_name="core_identity", index=False)
        _sanitize_frame(core_identity_detail).to_excel(writer, sheet_name="core_identity_rows", index=False)
        _sanitize_frame(script_limited_policy_summary).to_excel(writer, sheet_name="script_policy", index=False)
        _sanitize_frame(script_limited_policy_detail).to_excel(writer, sheet_name="script_policy_rows", index=False)
        _sanitize_frame(latin_residual_policy_summary).to_excel(writer, sheet_name="latin_residual_policy", index=False)
        _sanitize_frame(latin_residual_policy_detail).to_excel(writer, sheet_name="latin_residual_rows", index=False)
        _sanitize_frame(alignment_guard_summary).to_excel(writer, sheet_name="alignment_guard", index=False)
        _sanitize_frame(alignment_context_gaps).to_excel(writer, sheet_name="alignment_context_gaps", index=False)
        _sanitize_frame(alignment_intelligence_summary).to_excel(writer, sheet_name="alignment_intelligence", index=False)
        _sanitize_frame(alignment_intelligence_rows).to_excel(writer, sheet_name="alignment_intel_rows", index=False)
        _sanitize_frame(display_reconstruction_summary).to_excel(writer, sheet_name="display_reconstruct", index=False)
        _sanitize_frame(display_reconstruction_rows).to_excel(writer, sheet_name="display_recon_rows", index=False)
        _sanitize_frame(evidence_confidence_summary).to_excel(writer, sheet_name="evidence_conf", index=False)
        _sanitize_frame(evidence_confidence_rows).to_excel(writer, sheet_name="evidence_conf_rows", index=False)
        _sanitize_frame(evidence_budget_summary).to_excel(writer, sheet_name="evidence_budget", index=False)
        _sanitize_frame(evidence_budget_rows).to_excel(writer, sheet_name="evidence_budget_rows", index=False)
        _sanitize_frame(evidence_scheduler_summary).to_excel(writer, sheet_name="evidence_scheduler", index=False)
        _sanitize_frame(evidence_scheduler_rows).to_excel(writer, sheet_name="evidence_sched_rows", index=False)
        _sanitize_frame(character_reocr_debug_summary).to_excel(writer, sheet_name="reocr_debug_summary", index=False)
        _sanitize_frame(character_reocr_debug).to_excel(writer, sheet_name="reocr_debug", index=False)
        _sanitize_frame(character_acquisition_summary).to_excel(writer, sheet_name="char_acq_summary", index=False)
        _sanitize_frame(character_acquisition_rows).to_excel(writer, sheet_name="char_acq_rows", index=False)
        _sanitize_frame(character_acquisition_heatmap).to_excel(writer, sheet_name="char_acq_heatmap", index=False)
        _sanitize_frame(character_position_summary).to_excel(writer, sheet_name="char_pos_summary", index=False)
        _sanitize_frame(character_position_rows).to_excel(writer, sheet_name="char_pos_positions", index=False)
        _sanitize_frame(character_position_rank_rows).to_excel(writer, sheet_name="char_pos_rank", index=False)
        _sanitize_frame(pd.DataFrame([ocr_evidence_payload.get("summary", {})])).to_excel(writer, sheet_name="ocr_evidence_summary", index=False)
        _sanitize_frame(pd.DataFrame(ocr_evidence_payload.get("status_summary", []))).to_excel(writer, sheet_name="ocr_evidence_status", index=False)
        _sanitize_frame(ocr_evidence_rows).to_excel(writer, sheet_name="ocr_evidence_rows", index=False)
        _sanitize_frame(ocr_evidence_fragments).to_excel(writer, sheet_name="ocr_evidence_fragments", index=False)
        _sanitize_frame(detail).to_excel(writer, sheet_name="details", index=False)
        _sanitize_frame(failures).to_excel(writer, sheet_name="failures", index=False)

    reocr_debug_xlsx_path = output_dir / "character_reocr_debug_report.xlsx"
    with pd.ExcelWriter(reocr_debug_xlsx_path, engine="openpyxl") as writer:
        _sanitize_frame(character_reocr_debug_summary).to_excel(writer, sheet_name="summary", index=False)
        _sanitize_frame(character_reocr_debug).to_excel(writer, sheet_name="details", index=False)

    character_acquisition_xlsx_path = output_dir / "character_acquisition_report.xlsx"
    with pd.ExcelWriter(character_acquisition_xlsx_path, engine="openpyxl") as writer:
        _sanitize_frame(character_acquisition_summary).to_excel(writer, sheet_name="summary", index=False)
        _sanitize_frame(character_acquisition_rows).to_excel(writer, sheet_name="details", index=False)
        _sanitize_frame(character_acquisition_heatmap).to_excel(writer, sheet_name="heatmap", index=False)

    character_position_xlsx_path = output_dir / "character_position_intelligence_report.xlsx"
    with pd.ExcelWriter(character_position_xlsx_path, engine="openpyxl") as writer:
        _sanitize_frame(character_position_summary).to_excel(writer, sheet_name="summary", index=False)
        _sanitize_frame(character_position_rows).to_excel(writer, sheet_name="positions", index=False)
        _sanitize_frame(character_position_rank_rows).to_excel(writer, sheet_name="rank_actions", index=False)

    ocr_evidence_xlsx_path = output_dir / "ocr_evidence_report.xlsx"
    with pd.ExcelWriter(ocr_evidence_xlsx_path, engine="openpyxl") as writer:
        _sanitize_frame(pd.DataFrame([ocr_evidence_payload.get("summary", {})])).to_excel(writer, sheet_name="summary", index=False)
        _sanitize_frame(pd.DataFrame(ocr_evidence_payload.get("status_summary", []))).to_excel(writer, sheet_name="status_summary", index=False)
        _sanitize_frame(ocr_evidence_rows).to_excel(writer, sheet_name="rows", index=False)
        _sanitize_frame(ocr_evidence_fragments).to_excel(writer, sheet_name="fragments", index=False)

    gold_core_elimination_xlsx_path = output_dir / "gold_core_elimination_report.xlsx"
    with pd.ExcelWriter(gold_core_elimination_xlsx_path, engine="openpyxl") as writer:
        _sanitize_frame(gold_core_elimination_summary).to_excel(writer, sheet_name="summary", index=False)
        _sanitize_frame(gold_core_elimination_rows).to_excel(writer, sheet_name="details", index=False)

    gold_core_resolution_xlsx_path = output_dir / "gold_core_resolution_plan_report.xlsx"
    with pd.ExcelWriter(gold_core_resolution_xlsx_path, engine="openpyxl") as writer:
        _sanitize_frame(gold_core_resolution_summary).to_excel(writer, sheet_name="summary", index=False)
        _sanitize_frame(gold_core_resolution_plan).to_excel(writer, sheet_name="details", index=False)
    alignment_intelligence_xlsx_path = output_dir / "alignment_intelligence_report.xlsx"
    with pd.ExcelWriter(alignment_intelligence_xlsx_path, engine="openpyxl") as writer:
        _sanitize_frame(alignment_intelligence_summary).to_excel(writer, sheet_name="summary", index=False)
        _sanitize_frame(alignment_intelligence_rows).to_excel(writer, sheet_name="details", index=False)

    display_reconstruction_xlsx_path = output_dir / "display_reconstruction_report.xlsx"
    with pd.ExcelWriter(display_reconstruction_xlsx_path, engine="openpyxl") as writer:
        _sanitize_frame(display_reconstruction_summary).to_excel(writer, sheet_name="summary", index=False)
        _sanitize_frame(display_reconstruction_rows).to_excel(writer, sheet_name="details", index=False)

    evidence_confidence_xlsx_path = output_dir / "evidence_confidence_report.xlsx"
    with pd.ExcelWriter(evidence_confidence_xlsx_path, engine="openpyxl") as writer:
        _sanitize_frame(evidence_confidence_summary).to_excel(writer, sheet_name="summary", index=False)
        _sanitize_frame(evidence_confidence_rows).to_excel(writer, sheet_name="details", index=False)

    evidence_budget_xlsx_path = output_dir / "evidence_budget_report.xlsx"
    with pd.ExcelWriter(evidence_budget_xlsx_path, engine="openpyxl") as writer:
        _sanitize_frame(evidence_budget_summary).to_excel(writer, sheet_name="summary", index=False)
        _sanitize_frame(evidence_budget_rows).to_excel(writer, sheet_name="details", index=False)

    inference_xlsx_path = output_dir / "inference_report.xlsx"
    with pd.ExcelWriter(inference_xlsx_path, engine="openpyxl") as writer:
        pd.DataFrame([inference_summary]).to_excel(writer, sheet_name="summary", index=False)
        _sanitize_frame(inference_detail).to_excel(writer, sheet_name="details", index=False)

    runtime_metrics["report_write_ms"] = (time.perf_counter() - report_write_start) * 1000.0
    runtime_json_path = output_dir / "runtime_debug_report.json"
    runtime_xlsx_path = output_dir / "runtime_debug_report.xlsx"
    runtime_payload, runtime_phase_df = _build_runtime_debug_report(runtime_metrics, character_reocr_debug)
    runtime_json_path.write_text(json.dumps(_json_safe(runtime_payload), ensure_ascii=False, indent=2), encoding="utf-8")
    with pd.ExcelWriter(runtime_xlsx_path, engine="openpyxl") as writer:
        pd.DataFrame([runtime_payload.get("summary", {})]).to_excel(writer, sheet_name="summary", index=False)
        _sanitize_frame(runtime_phase_df).to_excel(writer, sheet_name="phases", index=False)
        _sanitize_frame(pd.DataFrame(runtime_payload.get("character_reocr_groups", []))).to_excel(writer, sheet_name="reocr_groups", index=False)

    print("\n===== GROUND TRUTH VALIDATION SUMMARY =====")
    print(pd.DataFrame(summary_rows).to_string(index=False))
    print("\nCategory summary:")
    print(category.to_string(index=False))
    print("\nFailure summary:")
    print(failure_summary.to_string(index=False))
    print(f"\nReport JSON:  {json_path}")
    print(f"Report Excel: {xlsx_path}")
    print(f"Inference JSON:  {inference_json_path}")
    print(f"Inference Excel: {inference_xlsx_path}")
    print(f"Character ReOCR Debug JSON:  {reocr_debug_json_path}")
    print(f"Character ReOCR Debug Excel: {reocr_debug_xlsx_path}")
    print(f"Character Acquisition JSON:   {character_acquisition_json_path}")
    print(f"Character Acquisition Excel:  {character_acquisition_xlsx_path}")
    print(f"Character Position JSON:      {character_position_json_path}")
    print(f"Character Position Excel:     {character_position_xlsx_path}")
    print(f"OCR Evidence JSON:  {ocr_evidence_json_path}")
    print(f"Display Reconstruction JSON:  {display_reconstruction_json_path}")
    print(f"Evidence Confidence JSON:      {evidence_confidence_json_path}")
    print(f"Evidence Budget JSON:          {evidence_budget_json_path}")
    print(f"OCR Evidence Excel: {ocr_evidence_xlsx_path}")
    print(f"Gold Core Resolution Plan JSON:  {gold_core_resolution_json_path}")
    print(f"Gold Core Resolution Plan Excel: {gold_core_resolution_xlsx_path}")
    print(f"Alignment Intelligence JSON:     {alignment_intelligence_json_path}")
    print(f"Alignment Intelligence Excel:    {alignment_intelligence_xlsx_path}")
    print(f"Runtime Debug JSON:  {runtime_json_path}")
    print(f"Runtime Debug Excel: {runtime_xlsx_path}")



def _discover_screenshots_dir(explicit_value: str | None, ocr_output_path: Path) -> tuple[Path | None, tempfile.TemporaryDirectory | None, str]:
    """Find screenshots for targeted character verification.

    Accepts either a directory or a ZIP file.  The default search order is
    deliberately project-local and conservative: the snapshot export's sibling
    `screenshots/`, project `screenshots/`, and common 551 benchmark zips.
    """
    temp_dir: tempfile.TemporaryDirectory | None = None
    candidates: list[Path] = []
    if explicit_value:
        candidates.append(Path(explicit_value))
    try:
        candidates.append(ocr_output_path.parent / "screenshots")
        candidates.append(ocr_output_path.parent.parent / "screenshots")
    except Exception:
        pass
    candidates.extend([
        Path("screenshots"),
        Path("551"),
        Path("551.zip"),
        Path("data/screenshots"),
        Path("input/screenshots"),
        Path("benchmarks/screenshots"),
    ])

    for candidate in candidates:
        if not candidate:
            continue
        if candidate.is_dir():
            return candidate, None, "directory"
        if candidate.is_file() and candidate.suffix.lower() == ".zip":
            temp_dir = tempfile.TemporaryDirectory(prefix="sentinel_char_reocr_")
            with zipfile.ZipFile(candidate) as archive:
                archive.extractall(temp_dir.name)
            return Path(temp_dir.name), temp_dir, "zip"
    return None, None, "not_found"

def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Sentinel OCR output against a Ground Truth Excel file.")
    parser.add_argument("--ground-truth", default="ground_truth/S6/server_551/top50_THP.xlsx", help="Path to manually curated ground truth Excel file.")
    parser.add_argument("--ocr-output", default="output/lastwar_export.xlsx", help="Path to Sentinel OCR export Excel file.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for validation reports.")
    parser.add_argument("--verify-characters", action="store_true", help="Force targeted screenshot re-OCR for Character Verification candidates. Conservative: adds evidence columns only and never changes Operational Truth.")
    parser.add_argument("--no-verify-characters", action="store_true", help="Disable automatic targeted character re-OCR.")
    parser.add_argument("--screenshots-dir", default=None, help="Screenshot directory or ZIP used for character re-OCR. If omitted, Sentinel auto-discovers common locations such as 551.zip and snapshot/screenshots.")
    args = parser.parse_args()

    ground_truth_path = Path(args.ground_truth)
    ocr_output_path = Path(args.ocr_output)
    output_dir = Path(args.output_dir)

    runtime_metrics: dict[str, float] = {}
    total_start = time.perf_counter()
    phase_start = time.perf_counter()
    gt = load_ground_truth(ground_truth_path)
    runtime_metrics["load_ground_truth_ms"] = (time.perf_counter() - phase_start) * 1000.0
    phase_start = time.perf_counter()
    ocr = load_ocr_output(ocr_output_path)
    runtime_metrics["load_ocr_export_ms"] = (time.perf_counter() - phase_start) * 1000.0
    phase_start = time.perf_counter()
    quarantine = load_ranking_guard_quarantine(ocr_output_path)
    runtime_metrics["load_quarantine_ms"] = (time.perf_counter() - phase_start) * 1000.0
    character_reader = None
    screenshots_path = None
    screenshots_temp = None
    verification_enabled = not args.no_verify_characters
    if verification_enabled:
        screenshots_path, screenshots_temp, screenshot_source_kind = _discover_screenshots_dir(args.screenshots_dir, ocr_output_path)
        if screenshots_path is not None:
            try:
                from parser.ocr import create_reader
                reader_start = time.perf_counter()
                character_reader = create_reader()
                runtime_metrics["ocr_reader_init_ms"] = (time.perf_counter() - reader_start) * 1000.0
                print(f"Character re-OCR enabled using {screenshot_source_kind}: {screenshots_path}")
            except Exception as exc:
                character_reader = None
                print(f"Character re-OCR evidence enabled without OCR provider ({exc}). Targets will be emitted as unresolved evidence.")
        elif args.verify_characters:
            raise FileNotFoundError("--verify-characters requested, but no screenshots directory or ZIP was found. Use --screenshots-dir <path>.")
        else:
            print("Character re-OCR skipped: no screenshots directory/ZIP found. Use --screenshots-dir <path> or --no-verify-characters.")
    phase_start = time.perf_counter()
    summary, detail, category = validate(gt, ocr, quarantine, character_reocr_reader=character_reader, screenshots_dir=screenshots_path)
    runtime_metrics["validation_ms"] = (time.perf_counter() - phase_start) * 1000.0
    runtime_metrics["total_runtime_ms"] = (time.perf_counter() - total_start) * 1000.0
    write_report(summary, detail, category, output_dir, runtime_metrics=runtime_metrics)
    if screenshots_temp is not None:
        screenshots_temp.cleanup()


if __name__ == "__main__":
    main()
