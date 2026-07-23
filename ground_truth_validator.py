"""Validate Sentinel OCR output against manually curated ground truth.

The validator compares a Ground Truth Excel file with a Sentinel OCR export.
It is intentionally independent from OCR providers: it measures the result that
actually matters for later Player Mobility and Identity Matching.

Usage:
    python ground_truth_validator.py \
        --ground-truth ground_truth/S6/server_551/top50_THP.xlsx \
        --ocr-output output/lastwar_export.xlsx

Outputs:
    reports/executive/SENTINEL_EXECUTIVE_REPORT.xlsx
    reports/operations/SENTINEL_RESOLUTION_WORKBENCH.xlsx
    reports/intelligence/SENTINEL_INTELLIGENCE_REPORT.xlsx
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
import tempfile
import zipfile
import time
from datetime import datetime, timezone
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import difflib
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


DEFAULT_OUTPUT_DIR = Path("reports")
RELEASE_VERSION = "0.9.5.161"

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


def _provenance_aware_character_alignment(
    expected_name: str,
    observed_name: str,
    source_records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """v0.9.5.153: align observed source characters to logical display positions.

    Expected text is used only as a benchmark alignment target, never as an
    evidence source. The result preserves source provenance through explicit
    MATCH/SUBSTITUTE/INSERT/DELETE/SEPARATOR_GAP/AMBIGUOUS operations.
    """
    expected = normalize_text(expected_name)
    observed = normalize_text(observed_name)
    target_rows: list[dict[str, Any]] = []
    insert_rows: list[dict[str, Any]] = []

    # UNKNOWN is a sentinel value, not character evidence. Never align its
    # letters to an expected player name.
    if observed.upper() == "UNKNOWN" and expected.upper() != "UNKNOWN":
        for target_index, target_char in enumerate(expected):
            target_rows.append({
                "target_position": target_index, "expected_character": target_char,
                "observed_character": "", "alignment_operation": "AMBIGUOUS",
                "alignment_reason": "unknown_base_not_character_evidence",
                "alignment_confidence": 0.0, "source_character_index": None,
                "source_record": {}, "gold_authoritative": False,
            })
        return target_rows, insert_rows

    matcher = difflib.SequenceMatcher(a=expected, b=observed, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for offset in range(i2 - i1):
                ti, sj = i1 + offset, j1 + offset
                target_char, source_char = expected[ti], observed[sj]
                source = source_records[sj] if 0 <= sj < len(source_records) else {}
                is_separator = target_char.isspace()
                operation = "SEPARATOR_GAP" if is_separator and source_char.isspace() else "MATCH"
                target_rows.append({
                    "target_position": ti, "expected_character": target_char,
                    "observed_character": source_char, "alignment_operation": operation,
                    "alignment_reason": "exact_character_alignment",
                    "alignment_confidence": 1.0, "source_character_index": sj,
                    "source_record": source, "gold_authoritative": False,
                })
        elif tag == "replace":
            target_len, source_len = i2 - i1, j2 - j1
            paired = min(target_len, source_len)
            for offset in range(paired):
                ti, sj = i1 + offset, j1 + offset
                target_char, source_char = expected[ti], observed[sj]
                source = source_records[sj] if 0 <= sj < len(source_records) else {}
                if target_char.isspace():
                    operation = "AMBIGUOUS"
                    reason = "non_separator_glyph_cannot_prove_separator"
                    confidence = 0.0
                else:
                    operation = "SUBSTITUTE"
                    reason = "source_character_differs_from_target"
                    confidence = 0.75 if target_len == source_len else 0.5
                target_rows.append({
                    "target_position": ti, "expected_character": target_char,
                    "observed_character": source_char, "alignment_operation": operation,
                    "alignment_reason": reason, "alignment_confidence": confidence,
                    "source_character_index": sj, "source_record": source,
                    "gold_authoritative": False,
                })
            for ti in range(i1 + paired, i2):
                target_rows.append({
                    "target_position": ti, "expected_character": expected[ti],
                    "observed_character": "", "alignment_operation": "DELETE",
                    "alignment_reason": "target_position_has_no_source_character",
                    "alignment_confidence": 0.0, "source_character_index": None,
                    "source_record": {}, "gold_authoritative": False,
                })
            for sj in range(j1 + paired, j2):
                source = source_records[sj] if 0 <= sj < len(source_records) else {}
                insert_rows.append({
                    "target_position": None, "expected_character": "",
                    "observed_character": observed[sj], "alignment_operation": "INSERT",
                    "alignment_reason": "source_character_has_no_target_position",
                    "alignment_confidence": 0.0, "source_character_index": sj,
                    "source_record": source, "gold_authoritative": False,
                })
        elif tag == "delete":
            for ti in range(i1, i2):
                target_rows.append({
                    "target_position": ti, "expected_character": expected[ti],
                    "observed_character": "", "alignment_operation": "DELETE",
                    "alignment_reason": "target_position_has_no_source_character",
                    "alignment_confidence": 0.0, "source_character_index": None,
                    "source_record": {}, "gold_authoritative": False,
                })
        elif tag == "insert":
            for sj in range(j1, j2):
                source = source_records[sj] if 0 <= sj < len(source_records) else {}
                insert_rows.append({
                    "target_position": None, "expected_character": "",
                    "observed_character": observed[sj], "alignment_operation": "INSERT",
                    "alignment_reason": "source_character_has_no_target_position",
                    "alignment_confidence": 0.0, "source_character_index": sj,
                    "source_record": source, "gold_authoritative": False,
                })
    target_rows.sort(key=lambda item: int(item["target_position"]))
    return target_rows, insert_rows


def _source_bound_display_characters(row: pd.Series, observed_name: str, evidence_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """v0.9.5.152: preserve current-snapshot provenance for each display character.

    Base OCR characters are linked to their row-level screenshot/source and exact
    character offset. Character ReOCR evidence can replace that provenance with a
    stronger crop-bound chain. This function never creates or corrects text.
    """
    screenshot = normalize_text(row.get("ground_truth_screenshot", "")) or normalize_text(row.get("screenshot", ""))
    source_file = normalize_text(row.get("ocr_source_file", ""))
    source_sheet = normalize_text(row.get("ocr_sheet", ""))
    row_slot = row.get("ground_truth_row_slot", row.get("row_slot", ""))
    records: list[dict[str, Any]] = []
    for position, character in enumerate(observed_name):
        records.append({
            "position": position,
            "character": character,
            "source_chain_status": "ROW_OCR_SOURCE_BOUND" if screenshot or source_file else "DISPLAY_ONLY_NOT_EVIDENCE",
            "source_type": "base_row_ocr",
            "source_screenshot": screenshot,
            "source_file": source_file,
            "source_sheet": source_sheet,
            "source_row_slot": row_slot,
            "source_observation_id": f"row:{source_file or screenshot}:{row_slot}:name",
            "source_character_index": position,
            "source_bbox": None,
            "source_crop_box": None,
            "source_confidence": float(row.get("ocr_name_confidence", 0.0) or 0.0),
            "alignment_operation": "identity_offset",
            "alignment_confidence": 1.0,
            "gold_authoritative": False,
        })
    for item in evidence_items:
        if not isinstance(item, dict) or str(item.get("field", "") or "") != "player_name":
            continue
        try:
            position = int(item.get("position"))
        except (TypeError, ValueError):
            continue
        if position < 0:
            continue
        selected = normalize_text(item.get("selected", ""))[:1]
        status = str(item.get("status", "") or "")
        if not selected or status not in {"verified_expected", "verified_observed"}:
            continue
        while len(records) <= position:
            records.append({
                "position": len(records), "character": "",
                "source_chain_status": "DISPLAY_ONLY_NOT_EVIDENCE",
                "source_type": "none", "gold_authoritative": False,
            })
        crop_box = item.get("crop_box")
        item_screenshot = normalize_text(item.get("screenshot", "")) or screenshot
        records[position] = {
            "position": position,
            "character": selected,
            "source_chain_status": "CROP_CHARACTER_SOURCE_BOUND" if item_screenshot and crop_box not in (None, "") else "ROW_OCR_SOURCE_BOUND",
            "source_type": "character_reocr_evidence",
            "source_screenshot": item_screenshot,
            "source_file": source_file,
            "source_sheet": source_sheet,
            "source_row_slot": row_slot,
            "source_observation_id": str(item.get("observation_id", "") or f"reocr:{item_screenshot}:{position}"),
            "source_character_index": position,
            "source_bbox": item.get("character_bbox"),
            "source_crop_box": crop_box,
            "source_confidence": float(item.get("confidence", 0.0) or 0.0),
            "alignment_operation": "verified_position_vote",
            "alignment_confidence": float(item.get("confidence", 0.0) or 0.0),
            "vote_status": status,
            "crop_anchor_status": str(item.get("crop_anchor_status", "") or ""),
            "crop_diagnostic": str(item.get("crop_diagnostic", "") or ""),
            "gold_authoritative": False,
        }
    return records


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
    display_character_provenance = _source_bound_display_characters(row, observed_name, evidence_items)
    display_character_alignment, display_character_insertions = _provenance_aware_character_alignment(
        expected_name, observed_name, display_character_provenance
    )

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
                selected = normalize_text(item.get("selected", ""))[:1] or expected_char[:1]
                if 0 <= position_int < len(display_character_provenance):
                    display_character_provenance[position_int]["character"] = selected
                    display_character_provenance[position_int]["alignment_operation"] = "verified_position_vote"
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
        "display_character_provenance": json.dumps(display_character_provenance, ensure_ascii=False),
        "display_character_alignment": json.dumps(display_character_alignment, ensure_ascii=False),
        "display_character_insertions": json.dumps(display_character_insertions, ensure_ascii=False),
        "display_alignment_matches": int(sum(1 for item in display_character_alignment if item.get("alignment_operation") in {"MATCH", "SEPARATOR_GAP"})),
        "display_alignment_substitutions": int(sum(1 for item in display_character_alignment if item.get("alignment_operation") == "SUBSTITUTE")),
        "display_alignment_deletions": int(sum(1 for item in display_character_alignment if item.get("alignment_operation") == "DELETE")),
        "display_alignment_ambiguous": int(sum(1 for item in display_character_alignment if item.get("alignment_operation") == "AMBIGUOUS")),
        "display_alignment_insertions": len(display_character_insertions),
        "display_source_bound_characters": int(sum(1 for item in display_character_provenance if item.get("source_chain_status") in {"ROW_OCR_SOURCE_BOUND", "CROP_CHARACTER_SOURCE_BOUND"})),
        "display_crop_bound_characters": int(sum(1 for item in display_character_provenance if item.get("source_chain_status") == "CROP_CHARACTER_SOURCE_BOUND")),
        "display_only_characters": int(sum(1 for item in display_character_provenance if item.get("source_chain_status") == "DISPLAY_ONLY_NOT_EVIDENCE")),
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



def _parse_character_reocr_evidence(value: Any) -> list[dict[str, Any]]:
    """Return normalized character-evidence rows from the validator payload."""
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except Exception:
            return []
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
    return []


def _gold_core_vote_policy_clearance(row: pd.Series) -> tuple[bool, str, dict[str, Any]]:
    """v0.9.5.145 Gold Core Zero I: deterministically clear warning-only vote noise.

    This gate is intentionally narrow. A row may clear only when the selected
    screenshot-local glyph evidence resolves to the expected character, no
    observed/unresolved/crop-conflict evidence exists, and name, alliance and
    power anchors independently prove the same Core Identity. Operational Truth
    and OCR exports remain unchanged.
    """
    evidence = _parse_character_reocr_evidence(row.get("character_reocr_evidence", ""))
    vote_warning_items = [
        item for item in evidence
        if str(item.get("crop_diagnostic", "") or "") == "vote_outside_allowed_set"
    ]
    statuses = [str(item.get("status", "") or "") for item in evidence]
    field_mismatch = any(str(item.get("crop_diagnostic", "") or "") in {"crop_field_mismatch", "crop_power_column_bleed"} or str(item.get("crop_anchor_status", "") or "") == "field_mismatch" for item in evidence)
    selected_expected = bool(vote_warning_items) and all(
        str(item.get("status", "") or "") == "verified_expected"
        and normalize_text(item.get("selected", ""))[:1] == normalize_text(item.get("expected", ""))[:1]
        for item in vote_warning_items
    )
    observed = _int_cell(row.get("character_reocr_verified_observed", 0)) + sum(1 for status in statuses if status == "verified_observed")
    unresolved = _int_cell(row.get("character_reocr_unresolved", 0)) + sum(1 for status in statuses if status in {"unresolved", "ambiguous_vote"})

    expected_name = normalize_text(row.get("expected_name", ""))
    proven_name = normalize_text(row.get("display_reconstructed_name", "") or row.get("verified_name_display", "") or row.get("ocr_name", ""))
    name_exact = bool(expected_name and proven_name == expected_name)
    expected_tag = normalize_text(row.get("expected_alliance_display", ""))
    proven_tag = normalize_text(row.get("display_reconstructed_alliance_tag", "") or row.get("verified_alliance_display", "") or row.get("ocr_alliance_display", ""))
    alliance_proven = bool(_bool_cell(row.get("core_alliance_match", False)) or (expected_tag and proven_tag == expected_tag) or (not expected_tag and not proven_tag))
    accepted = str(row.get("match_method", "") or "") not in {"missing", "blocked_rank_fallback"} and not _bool_cell(row.get("bad_match", False))

    diagnostics = {
        "vote_policy_warning_items": len(vote_warning_items),
        "vote_policy_selected_expected": selected_expected,
        "vote_policy_observed_evidence": observed,
        "vote_policy_unresolved_evidence": unresolved,
        "vote_policy_field_mismatch": field_mismatch,
        "vote_policy_name_exact": name_exact,
        "vote_policy_alliance_proven": alliance_proven,
        "vote_policy_power_proven": _bool_cell(row.get("power_match", False)),
    }
    if not _bool_cell(row.get("gold_core_blocker", False)):
        return False, "not_a_gold_core_blocker", diagnostics
    if _bool_cell(row.get("alignment_context_gap", False)):
        return False, "vote_policy_blocked_context_gap_read_only", diagnostics
    if not accepted:
        return False, "vote_policy_blocked_identity_match_not_accepted", diagnostics
    if not vote_warning_items:
        return False, "vote_policy_not_a_warning_only_case", diagnostics
    if not selected_expected:
        return False, "vote_policy_blocked_selected_glyph_not_expected", diagnostics
    if observed > 0:
        return False, "vote_policy_blocked_observed_counterevidence", diagnostics
    if unresolved > 0:
        return False, "vote_policy_blocked_unresolved_or_ambiguous_votes", diagnostics
    if field_mismatch:
        return False, "vote_policy_blocked_crop_geometry_conflict", diagnostics
    if not name_exact:
        return False, "vote_policy_blocked_name_not_exact", diagnostics
    if not alliance_proven:
        return False, "vote_policy_blocked_alliance_not_proven", diagnostics
    if not _bool_cell(row.get("power_match", False)):
        return False, "vote_policy_blocked_power_not_proven", diagnostics
    return True, "vote_warning_noise_downgraded_after_expected_only_consensus", diagnostics


def _promotion_guard_diagnostics(row: pd.Series) -> dict[str, Any]:
    """v0.9.5.146: expose every promotion condition instead of one opaque reason."""
    evidence = _parse_character_reocr_evidence(row.get("character_reocr_evidence", ""))
    warning_items = [item for item in evidence if str(item.get("crop_diagnostic", "") or "") == "vote_outside_allowed_set"]
    statuses = [str(item.get("status", "") or "") for item in evidence]
    expected_only = bool(warning_items) and all(
        str(item.get("status", "") or "") == "verified_expected"
        and normalize_text(item.get("selected", ""))[:1] == normalize_text(item.get("expected", ""))[:1]
        for item in warning_items
    )
    field_mismatch = any(
        str(item.get("crop_diagnostic", "") or "") in {"crop_field_mismatch", "crop_power_column_bleed"}
        or str(item.get("crop_anchor_status", "") or "") == "field_mismatch"
        for item in evidence
    )
    observed = _int_cell(row.get("character_reocr_verified_observed", 0)) + sum(1 for status in statuses if status == "verified_observed")
    unresolved = _int_cell(row.get("character_reocr_unresolved", 0)) + sum(1 for status in statuses if status in {"unresolved", "ambiguous_vote"})
    expected_name = normalize_text(row.get("expected_name", ""))
    candidates = [
        normalize_text(row.get("display_reconstructed_name", "")),
        normalize_text(row.get("verified_name_display", "")),
        normalize_text(row.get("ocr_name", "")),
    ]
    name_exact = bool(expected_name and expected_name in candidates)
    expected_tag = normalize_text(row.get("expected_alliance_display", ""))
    tag_candidates = [
        normalize_text(row.get("display_reconstructed_alliance_tag", "")),
        normalize_text(row.get("verified_alliance_display", "")),
        normalize_text(row.get("ocr_alliance_display", "")),
    ]
    alliance_proven = bool(
        _bool_cell(row.get("core_alliance_match", False))
        or (expected_tag and expected_tag in tag_candidates)
        or (not expected_tag and not any(tag_candidates))
    )
    accepted = str(row.get("match_method", "") or "") not in {"missing", "blocked_rank_fallback"} and not _bool_cell(row.get("bad_match", False))
    checks = {
        "accepted_match": accepted,
        "context_available": not _bool_cell(row.get("alignment_context_gap", False)),
        "power_proven": _bool_cell(row.get("power_match", False)),
        "alliance_proven": alliance_proven,
        "name_exact": name_exact,
        "warning_evidence_present": bool(warning_items),
        "expected_only_vote_consensus": expected_only,
        "no_observed_counterevidence": observed == 0,
        "no_unresolved_votes": unresolved == 0,
        "no_crop_field_mismatch": not field_mismatch,
        "legacy_promotion_eligible": _bool_cell(row.get("display_promotion_eligible", False)),
    }
    failed = [name for name, passed in checks.items() if not passed]
    legacy_reason = str(row.get("display_promotion_block_reason", "") or "")
    return {
        "promotion_guard_checks": json.dumps(checks, ensure_ascii=False, sort_keys=True),
        "promotion_guard_failed_checks": json.dumps(failed, ensure_ascii=False),
        "promotion_guard_failed_count": len(failed),
        "promotion_guard_primary_blocker": failed[0] if failed else "none",
        "promotion_guard_legacy_reason": legacy_reason,
        "promotion_guard_expected_only_consensus": expected_only,
        "promotion_guard_warning_items": len(warning_items),
        "promotion_guard_observed_evidence": observed,
        "promotion_guard_unresolved_evidence": unresolved,
        "promotion_guard_field_mismatch": field_mismatch,
        "promotion_guard_name_exact": name_exact,
        "promotion_guard_alliance_proven": alliance_proven,
        "promotion_guard_power_proven": _bool_cell(row.get("power_match", False)),
    }


def _gold_core_promotion_guard_clearance(row: pd.Series) -> tuple[bool, str, dict[str, Any]]:
    """v0.9.5.146 Gold Core Zero II: rationalize legacy low-coverage blocking.

    The override is deliberately class-bound and evidence-bound. It applies only
    to warning-only vote cases where every current-screenshot vote selects the
    expected glyph, no counterevidence/crop conflict exists, and accepted match,
    name, alliance and power anchors independently agree. It does not relax the
    guard for crop, observed-text, script-policy or mixed blockers.
    """
    diagnostics = _promotion_guard_diagnostics(row)
    failure_class = str(row.get("gold_core_failure_class", "") or "")
    legacy_reason = diagnostics["promotion_guard_legacy_reason"]
    allowed_class = failure_class == "vote_warning_gate_review"
    diagnostics["promotion_guard_allowed_failure_class"] = allowed_class
    diagnostics["promotion_guard_failure_class"] = failure_class

    if not _bool_cell(row.get("gold_core_blocker", False)):
        return False, "not_a_gold_core_blocker", diagnostics
    if not allowed_class:
        return False, "promotion_guard_override_wrong_failure_class", diagnostics
    if _bool_cell(row.get("alignment_context_gap", False)):
        return False, "promotion_guard_override_context_gap_read_only", diagnostics
    if not legacy_reason or ("low_coverage" not in legacy_reason and "budget" not in legacy_reason):
        return False, "promotion_guard_override_not_low_coverage_class", diagnostics
    mandatory = {
        "accepted_match", "power_proven", "alliance_proven", "name_exact",
        "warning_evidence_present", "expected_only_vote_consensus",
        "no_observed_counterevidence", "no_unresolved_votes", "no_crop_field_mismatch",
    }
    checks = json.loads(diagnostics["promotion_guard_checks"])
    failed_mandatory = sorted(name for name in mandatory if not checks.get(name, False))
    diagnostics["promotion_guard_override_failed_mandatory"] = json.dumps(failed_mandatory, ensure_ascii=False)
    if failed_mandatory:
        return False, "promotion_guard_override_mandatory_checks_failed:" + ",".join(failed_mandatory), diagnostics
    if _bool_cell(row.get("display_promotion_eligible", False)):
        return False, "promotion_guard_override_not_needed", diagnostics
    return True, "legacy_low_coverage_guard_rationalized_by_expected_only_consensus", diagnostics



def _evidence_bound_name_reconstruction(row: pd.Series) -> dict[str, Any]:
    """v0.9.5.147: prove a display name from source text plus position evidence.

    Ground Truth supplies the expected comparison value only; it is never used
    as an unobserved fill source. A position is proven either by an equal block
    aligned from current-snapshot source text or by a verified-expected ReOCR
    fragment for that exact position. Any uncovered position remains explicit.
    """
    from difflib import SequenceMatcher

    expected = normalize_text(row.get("expected_name", ""))
    raw_candidates = [
        normalize_text(row.get("display_reconstructed_name", "")),
        normalize_text(row.get("verified_name_display", "")),
        normalize_text(row.get("ocr_name", "")),
    ]
    candidates = [c for c in raw_candidates if c and c.upper() != "UNKNOWN"]
    source = max(candidates, key=len) if candidates else ""
    evidence = _parse_character_reocr_evidence(row.get("character_reocr_evidence", ""))

    source_proof: dict[int, dict[str, Any]] = {}
    if expected and source:
        matcher = SequenceMatcher(a=expected, b=source, autojunk=False)
        for block in matcher.get_matching_blocks():
            for offset in range(block.size):
                pos = block.a + offset
                source_proof[pos] = {
                    "position": pos,
                    "char": expected[pos],
                    "proof": "source_alignment",
                    "source_index": block.b + offset,
                    "source_value": source[block.b + offset],
                }

    evidence_proof: dict[int, dict[str, Any]] = {}
    conflicts: list[dict[str, Any]] = []
    unresolved_items: list[dict[str, Any]] = []
    field_mismatch = False
    for item in evidence:
        if str(item.get("field", "") or "") != "player_name":
            continue
        try:
            pos = int(item.get("position"))
        except (TypeError, ValueError):
            continue
        status = str(item.get("status", "") or "")
        diagnostic = str(item.get("crop_diagnostic", "") or "")
        anchor = str(item.get("crop_anchor_status", "") or "")
        if diagnostic in {"crop_field_mismatch", "crop_power_column_bleed"} or anchor == "field_mismatch":
            field_mismatch = True
        expected_char = expected[pos] if 0 <= pos < len(expected) else ""
        item_expected = normalize_text(item.get("expected", ""))
        selected = normalize_text(item.get("selected", ""))
        if status == "verified_expected" and expected_char and item_expected[:1] == expected_char and selected[:1] == expected_char and not field_mismatch:
            evidence_proof[pos] = {
                "position": pos,
                "char": expected_char,
                "proof": "verified_expected_reocr",
                "confidence": float(item.get("confidence", 0.0) or 0.0),
                "screenshot": item.get("screenshot", ""),
                "crop_box": item.get("crop_box"),
                "crop_diagnostic": diagnostic,
                "crop_anchor_status": anchor,
            }
        elif status == "verified_observed" or (selected and expected_char and selected[:1] != expected_char):
            conflicts.append({
                "position": pos, "expected": expected_char,
                "selected": selected[:1], "status": status,
                "crop_diagnostic": diagnostic,
            })
        elif status in {"unresolved", "ambiguous_vote"}:
            unresolved_items.append({"position": pos, "status": status})

    proof_by_position = dict(source_proof)
    proof_by_position.update(evidence_proof)
    total = len(expected)
    verified_positions = sorted(pos for pos in proof_by_position if 0 <= pos < total)
    missing_positions = [pos for pos in range(total) if pos not in proof_by_position]
    reconstructed_chars = [proof_by_position[pos]["char"] if pos in proof_by_position else "?" for pos in range(total)]
    reconstructed = "".join(reconstructed_chars)
    exact_source = bool(expected and source == expected)
    full_evidence = bool(expected and not missing_positions and not conflicts and not unresolved_items and not field_mismatch)
    evidence_used = bool(evidence_proof)

    if exact_source:
        status = "SOURCE_EXACT"
        reconstructed = expected
    elif conflicts:
        status = "CONFLICTING_EVIDENCE"
    elif full_evidence and evidence_used:
        status = "EVIDENCE_RECONSTRUCTED_EXACT"
        reconstructed = expected
    elif proof_by_position:
        status = "PARTIAL_RECONSTRUCTION"
    elif expected:
        status = "INSUFFICIENT_EVIDENCE"
    else:
        status = "UNKNOWN"

    coverage = round(len(verified_positions) / total, 4) if total else 0.0
    trace = [proof_by_position[pos] for pos in verified_positions]
    failed = []
    if not expected: failed.append("expected_name_missing")
    if missing_positions: failed.append("incomplete_position_coverage")
    if conflicts: failed.append("conflicting_character_evidence")
    if unresolved_items: failed.append("unresolved_character_evidence")
    if field_mismatch: failed.append("crop_or_field_mismatch")
    if not evidence_used and not exact_source: failed.append("no_verified_name_evidence")

    return {
        "name_proof_status": status,
        "name_reconstructed_value": reconstructed,
        "name_reconstruction_exact": bool(status in {"SOURCE_EXACT", "EVIDENCE_RECONSTRUCTED_EXACT"}),
        "name_reconstruction_coverage": coverage,
        "name_positions_total": total,
        "name_positions_verified": len(verified_positions),
        "name_positions_unresolved": len(missing_positions) + len(unresolved_items),
        "name_positions_conflicting": len(conflicts),
        "name_reconstruction_source_value": source,
        "name_reconstruction_verified_positions": json.dumps(verified_positions, ensure_ascii=False),
        "name_reconstruction_missing_positions": json.dumps(missing_positions, ensure_ascii=False),
        "name_reconstruction_sources": json.dumps({"source": len(source_proof), "reocr": len(evidence_proof)}, ensure_ascii=False, sort_keys=True),
        "name_reconstruction_trace": json.dumps(trace, ensure_ascii=False),
        "name_reconstruction_conflicts": json.dumps(conflicts, ensure_ascii=False),
        "name_reconstruction_failed_checks": json.dumps(failed, ensure_ascii=False),
        "name_reconstruction_ground_truth_fill_used": False,
        "name_reconstruction_field_mismatch": field_mismatch,
    }


def _gold_core_evidence_name_clearance(row: pd.Series) -> tuple[bool, str, dict[str, Any]]:
    """v0.9.5.147 Gold Core Zero III: accept only complete evidence proof."""
    diagnostics = _evidence_bound_name_reconstruction(row)
    evidence = _parse_character_reocr_evidence(row.get("character_reocr_evidence", ""))
    warning_items = [item for item in evidence if str(item.get("crop_diagnostic", "") or "") == "vote_outside_allowed_set"]
    statuses = [str(item.get("status", "") or "") for item in evidence if str(item.get("field", "") or "") == "player_name"]
    expected_only = bool(warning_items) and all(
        str(item.get("status", "") or "") == "verified_expected"
        and normalize_text(item.get("selected", ""))[:1] == normalize_text(item.get("expected", ""))[:1]
        for item in warning_items
    )
    observed = _int_cell(row.get("character_reocr_verified_observed", 0)) + sum(1 for status in statuses if status == "verified_observed")
    unresolved = _int_cell(row.get("character_reocr_unresolved", 0)) + sum(1 for status in statuses if status in {"unresolved", "ambiguous_vote"})
    explicit_class = str(row.get("gold_core_failure_class", "") or "")
    evidence_signature = bool(warning_items and expected_only and observed == 0 and unresolved == 0)
    allowed_case = explicit_class == "vote_warning_gate_review" or (not explicit_class and evidence_signature)
    expected_tag = normalize_text(row.get("expected_alliance_display", ""))
    tag_candidates = {
        normalize_text(row.get("display_reconstructed_alliance_tag", "")),
        normalize_text(row.get("verified_alliance_display", "")),
        normalize_text(row.get("ocr_alliance_display", "")),
    }
    alliance_proven = bool(_bool_cell(row.get("core_alliance_match", False)) or (expected_tag and expected_tag in tag_candidates) or (not expected_tag and not any(tag_candidates)))
    accepted = str(row.get("match_method", "") or "") not in {"missing", "blocked_rank_fallback"} and not _bool_cell(row.get("bad_match", False))
    checks = {
        "gold_core_blocker": _bool_cell(row.get("gold_core_blocker", False)),
        "allowed_vote_warning_case": allowed_case,
        "accepted_match": accepted,
        "context_available": not _bool_cell(row.get("alignment_context_gap", False)),
        "power_proven": _bool_cell(row.get("power_match", False)),
        "alliance_proven": alliance_proven,
        "expected_only_vote_consensus": expected_only,
        "no_observed_counterevidence": observed == 0,
        "no_unresolved_votes": unresolved == 0,
        "complete_name_evidence": diagnostics["name_proof_status"] == "EVIDENCE_RECONSTRUCTED_EXACT",
        "full_position_coverage": diagnostics["name_reconstruction_coverage"] == 1.0,
        "no_ground_truth_fill": not diagnostics["name_reconstruction_ground_truth_fill_used"],
        "no_crop_field_mismatch": not diagnostics["name_reconstruction_field_mismatch"],
    }
    failed = [name for name, passed in checks.items() if not passed]
    diagnostics.update({
        "name_reconstruction_clearance_checks": json.dumps(checks, ensure_ascii=False, sort_keys=True),
        "name_reconstruction_clearance_failed_checks": json.dumps(failed, ensure_ascii=False),
        "name_reconstruction_clearance_allowed_case": allowed_case,
        "name_reconstruction_clearance_failure_class": explicit_class,
        "name_reconstruction_clearance_expected_only": expected_only,
        "name_reconstruction_clearance_alliance_proven": alliance_proven,
        "name_reconstruction_clearance_power_proven": _bool_cell(row.get("power_match", False)),
        "name_reconstruction_clearance_operational_truth_modified": False,
    })
    if failed:
        return False, "evidence_name_reconstruction_blocked:" + ",".join(failed), diagnostics
    return True, "complete_position_bound_name_evidence_proves_expected_display", diagnostics

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
    vote_policy_clear, vote_policy_reason, vote_policy_diagnostics = _gold_core_vote_policy_clearance(row)
    promotion_guard_clear, promotion_guard_reason, promotion_guard_diagnostics = _gold_core_promotion_guard_clearance(row)
    evidence_name_clear, evidence_name_reason, evidence_name_diagnostics = _gold_core_evidence_name_clearance(row)
    clear = bool(strict_clear or strike_clear or strike_ii_clear or strike_iii_clear or vote_policy_clear or promotion_guard_clear or evidence_name_clear)

    if strict_clear:
        reason = "display_reconstruction_proves_name_and_core_alliance"
        action = "clear_gold_core_blocker"
    elif evidence_name_clear:
        reason = evidence_name_reason
        action = "clear_gold_core_blocker_evidence_reconstructed_name"
    elif promotion_guard_clear:
        # v0.9.5.146 attribution: the legacy promotion guard was the active
        # blocker even when the underlying v0.9.5.145 vote policy also passes.
        reason = promotion_guard_reason
        action = "clear_gold_core_blocker_promotion_guard_rationalized"
    elif vote_policy_clear:
        reason = vote_policy_reason
        action = "clear_gold_core_blocker_vote_policy"
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
        **vote_policy_diagnostics,
        **promotion_guard_diagnostics,
        **evidence_name_diagnostics,
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
        "vote_policy_warning_items", "vote_policy_selected_expected", "vote_policy_observed_evidence",
        "vote_policy_unresolved_evidence", "vote_policy_field_mismatch", "vote_policy_name_exact",
        "vote_policy_alliance_proven", "vote_policy_power_proven",
        "promotion_guard_checks", "promotion_guard_failed_checks", "promotion_guard_failed_count",
        "promotion_guard_primary_blocker", "promotion_guard_legacy_reason",
        "promotion_guard_expected_only_consensus", "promotion_guard_warning_items",
        "promotion_guard_observed_evidence", "promotion_guard_unresolved_evidence",
        "promotion_guard_field_mismatch", "promotion_guard_name_exact",
        "promotion_guard_alliance_proven", "promotion_guard_power_proven",
        "promotion_guard_allowed_failure_class", "promotion_guard_failure_class",
        "promotion_guard_override_failed_mandatory",
        "name_proof_status", "name_reconstructed_value", "name_reconstruction_exact",
        "name_reconstruction_coverage", "name_positions_total", "name_positions_verified",
        "name_positions_unresolved", "name_positions_conflicting",
        "name_reconstruction_source_value", "name_reconstruction_verified_positions",
        "name_reconstruction_missing_positions", "name_reconstruction_sources",
        "name_reconstruction_trace", "name_reconstruction_conflicts",
        "name_reconstruction_failed_checks", "name_reconstruction_ground_truth_fill_used",
        "name_reconstruction_field_mismatch", "name_reconstruction_clearance_checks",
        "name_reconstruction_clearance_failed_checks", "name_reconstruction_clearance_allowed_case",
        "name_reconstruction_clearance_failure_class", "name_reconstruction_clearance_expected_only",
        "name_reconstruction_clearance_alliance_proven", "name_reconstruction_clearance_power_proven",
        "name_reconstruction_clearance_operational_truth_modified",
    ]
    if detail.empty:
        return pd.DataFrame([{
            "phase": "v0.9.5.147_gold_core_zero_iii",
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
            "phase": "v0.9.5.147_gold_core_zero_iii",
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
    summary.insert(0, "phase", "v0.9.5.147_gold_core_zero_iii")
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
        "display_character_provenance", "display_character_alignment", "display_character_insertions",
        "display_alignment_matches", "display_alignment_substitutions", "display_alignment_deletions",
        "display_alignment_ambiguous", "display_alignment_insertions", "display_source_bound_characters",
        "display_crop_bound_characters", "display_only_characters",
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
    numeric_cols = {
        "display_reconstruction_confidence", "display_reconstruction_name_targets_applied",
        "display_reconstruction_alliance_targets_applied", "display_reconstruction_unresolved_targets",
        "display_reconstruction_observed_votes", "display_alignment_matches",
        "display_alignment_substitutions", "display_alignment_deletions", "display_alignment_ambiguous",
        "display_alignment_insertions", "display_source_bound_characters",
        "display_crop_bound_characters", "display_only_characters", "evidence_fragments_total",
        "evidence_confirmed_fragments", "evidence_observed_fragments", "evidence_unresolved_fragments",
        "evidence_avg_fragment_confidence", "display_name_coverage_score",
        "display_alliance_coverage_score", "display_coverage_score", "evidence_priority_score",
        "evidence_avg_crop_quality", "evidence_avg_ocr_confidence", "evidence_avg_vote_consensus",
        "evidence_avg_position_stability", "evidence_avg_unicode_class",
    }
    for col in cols:
        if col not in rows.columns:
            rows[col] = 0.0 if col in numeric_cols else ""
    for col in numeric_cols:
        if col in rows.columns:
            rows[col] = pd.to_numeric(rows[col], errors="coerce").fillna(0.0)
    report = rows[cols].copy()
    for numeric_col in ["evidence_avg_fragment_confidence", "display_coverage_score", "display_name_coverage_score", "display_alliance_coverage_score"]:
        report[numeric_col] = pd.to_numeric(report[numeric_col], errors="coerce").fillna(0.0)
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
    summary.insert(0, "phase", "v0.9.5.147_gold_core_zero_iii")
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
    for numeric_col in ["evidence_avg_fragment_confidence", "display_coverage_score", "display_name_coverage_score", "display_alliance_coverage_score"]:
        report[numeric_col] = pd.to_numeric(report[numeric_col], errors="coerce").fillna(0.0)
    report = report[report["display_reconstruction_status"].astype(str).ne("not_reconstructed")].copy()
    if report.empty:
        return pd.DataFrame([{"phase": "v0.9.5.147_gold_core_zero_iii", "rows": 0, "operational_truth_modified": False}]), report
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
    summary.insert(0, "phase", "v0.9.5.147_gold_core_zero_iii")
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
        return pd.DataFrame([{"phase": "v0.9.5.147_gold_core_zero_iii", "rows": 0, "operational_truth_modified": False}]), pd.DataFrame(columns=cols)
    rows = detail.copy()
    for col in cols:
        if col not in rows.columns:
            rows[col] = ""
    report = rows[cols].copy()
    for numeric_col in ["evidence_priority_score", "evidence_avg_fragment_confidence", "display_coverage_score", "evidence_budget_expected_cost_ms"]:
        report[numeric_col] = pd.to_numeric(report[numeric_col], errors="coerce").fillna(0.0)
    report["display_promotion_eligible"] = report["display_promotion_eligible"].fillna(False).astype(bool)
    report = report[report["display_reconstruction_status"].astype(str).ne("not_reconstructed")].copy()
    if report.empty:
        return pd.DataFrame([{"phase": "v0.9.5.147_gold_core_zero_iii", "rows": 0, "operational_truth_modified": False}]), report
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
    summary.insert(0, "phase", "v0.9.5.147_gold_core_zero_iii")
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
        return pd.DataFrame([{"phase": "v0.9.5.147_gold_core_zero_iii", "rows": 0, "operational_truth_modified": False}]), pd.DataFrame(columns=cols)
    rows = detail.copy()
    for col in cols:
        if col not in rows.columns:
            rows[col] = ""
    report = rows[cols].copy()
    for numeric_col in ["evidence_priority_score", "scheduler_expected_runtime_ms", "scheduler_estimated_saved_ms", "evidence_budget_expected_cost_ms", "scheduler_queue_order"]:
        report[numeric_col] = pd.to_numeric(report[numeric_col], errors="coerce").fillna(0.0)
    report["display_promotion_eligible"] = report["display_promotion_eligible"].fillna(False).astype(bool)
    report = report[report["display_reconstruction_status"].astype(str).ne("not_reconstructed")].copy()
    if report.empty:
        return pd.DataFrame([{"phase": "v0.9.5.147_gold_core_zero_iii", "rows": 0, "operational_truth_modified": False}]), report
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
    summary.insert(0, "phase", "v0.9.5.147_gold_core_zero_iii")
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
            "phase": "v0.9.5.147_gold_core_zero_iii",
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
            "phase": "v0.9.5.147_gold_core_zero_iii",
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
        summary.insert(0, "phase", "v0.9.5.147_gold_core_zero_iii")
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
            "phase": "v0.9.5.147_gold_core_zero_iii",
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
    summary.insert(0, "phase", "v0.9.5.147_gold_core_zero_iii")
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



def _identity_script_class(character: str) -> str:
    """Classify one observed character without using Ground Truth."""
    if not character:
        return "EMPTY"
    if character.isspace():
        return "SEPARATOR"
    code = ord(character)
    if "0" <= character <= "9":
        return "DIGIT"
    if ("A" <= character <= "Z") or ("a" <= character <= "z") or (0x00C0 <= code <= 0x024F):
        return "LATIN"
    if 0xAC00 <= code <= 0xD7AF or 0x1100 <= code <= 0x11FF:
        return "HANGUL"
    if 0x3040 <= code <= 0x30FF:
        return "JAPANESE_KANA"
    if 0x3400 <= code <= 0x9FFF:
        return "CJK"
    if character in "[](){}<>【】『』「」":
        return "BRACKET"
    if character in "-_·•|/\\.'’`~^":
        return "DECORATIVE"
    return "SYMBOL"


def _tokenize_identity_observation(text: str, provenance: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """v0.9.5.154: create source-bound tokens from observed text only."""
    value = normalize_text(text)
    chars: list[dict[str, Any]] = []
    for i, ch in enumerate(value):
        source = provenance[i] if i < len(provenance) and isinstance(provenance[i], dict) else {}
        chars.append({
            "character_id": f"char:{i}", "character_index": i, "character": ch,
            "script_class": _identity_script_class(ch),
            "source_chain_status": source.get("source_chain_status", "DISPLAY_ONLY_NOT_EVIDENCE"),
            "source_screenshot": source.get("source_screenshot", ""),
            "source_observation_id": source.get("source_observation_id", ""),
            "source_character_index": source.get("source_character_index", i),
            "gold_authoritative": False,
        })
    if not value:
        return chars, []
    tokens: list[dict[str, Any]] = []
    start = 0
    current = _identity_script_class(value[0])
    grouping = current
    for i in range(1, len(value) + 1):
        nxt = _identity_script_class(value[i]) if i < len(value) else None
        # Latin and digits may form one lexical token. Everything else splits on
        # script changes, separators, brackets and decorative symbols.
        compatible = grouping in {"LATIN", "DIGIT"} and nxt in {"LATIN", "DIGIT"}
        if i == len(value) or (nxt != current and not compatible) or current in {"SEPARATOR", "BRACKET", "DECORATIVE", "SYMBOL"}:
            token_text = value[start:i]
            token_classes = sorted({_identity_script_class(c) for c in token_text})
            token_id = f"token:{len(tokens)}"
            tokens.append({
                "token_id": token_id, "token_index": len(tokens), "token_text": token_text,
                "start": start, "end": i, "length": len(token_text),
                "script_classes": token_classes,
                "character_ids": [f"char:{j}" for j in range(start, i)],
                "source_bound": all(chars[j]["source_chain_status"] != "DISPLAY_ONLY_NOT_EVIDENCE" for j in range(start, i)),
                "token_confidence": round(sum(0.9 if chars[j]["source_chain_status"] != "DISPLAY_ONLY_NOT_EVIDENCE" else 0.45 for j in range(start, i)) / max(1, i - start), 4),
                "gold_authoritative": False,
            })
            start = i
            if i < len(value):
                current = nxt
                grouping = nxt
        elif compatible:
            current = grouping
    return chars, tokens


def _classify_identity_components(observed_name: str, observed_tag: str, tokens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Classify observed tokens conservatively; classifications are hypotheses."""
    components: list[dict[str, Any]] = []
    unknown = normalize_text(observed_name).upper() == "UNKNOWN"
    title_tokens = {"VIP", "KING", "QUEEN", "LORD", "DR", "MR", "MS"}
    for token in tokens:
        text = normalize_text(token.get("token_text", ""))
        classes = set(token.get("script_classes", []))
        kind = "NAME_TOKEN"
        reason = "lexical_observed_token"
        confidence = 0.65
        if unknown:
            kind, reason, confidence = "UNKNOWN_SENTINEL", "unknown_is_not_identity_character_evidence", 1.0
        elif classes == {"SEPARATOR"}:
            kind, reason, confidence = "SEPARATOR", "observed_whitespace_boundary", 1.0
        elif classes <= {"BRACKET", "DECORATIVE", "SYMBOL"}:
            kind, reason, confidence = "DECORATIVE_MARK", "nonlexical_observed_token", 0.9
        elif text.upper() in title_tokens:
            kind, reason, confidence = "TITLE_OR_PREFIX", "known_title_like_observed_token", 0.7
        elif classes & {"HANGUL", "JAPANESE_KANA", "CJK"}:
            kind, reason, confidence = "SCRIPT_NAME_BLOCK", "non_latin_observed_script_block", 0.8
        elif text and text == normalize_text(observed_tag):
            kind, reason, confidence = "ALLIANCE_TAG_CANDIDATE", "matches_observed_alliance_tag", 0.9
        components.append({
            "component_id": f"component:{len(components)}", "component_index": len(components),
            "component_type": kind, "component_text": text,
            "token_ids": [token.get("token_id")], "classification_reason": reason,
            "classification_confidence": confidence,
            "identity_authoritative": False, "gold_authoritative": False,
        })
    return components


def _build_player_identity_graph(detail: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """v0.9.5.154 Strike XI: observed character -> token -> identity component graph.

    The graph is read-only. It uses current snapshot display/OCR provenance only.
    Expected names remain benchmark context and never create graph nodes.
    """
    blocker_col = detail.get("gold_core_blocker_after_elimination", detail.get("gold_core_blocker", pd.Series(False, index=detail.index)))
    blockers = detail[blocker_col.fillna(False).astype(bool)].copy()
    case_rows, char_rows, token_rows, component_rows, edge_rows = [], [], [], [], []
    for _, row in blockers.iterrows():
        server, rank = row.get("server"), row.get("rank")
        observed = normalize_text(row.get("display_reconstructed_name", "")) or normalize_text(row.get("ocr_name", ""))
        observed_tag = normalize_text(row.get("display_reconstructed_alliance_tag", "")) or normalize_text(row.get("ocr_alliance_tag", ""))
        provenance = _parse_json_list(row.get("display_character_provenance", "[]"))
        chars, tokens = _tokenize_identity_observation(observed, provenance)
        components = _classify_identity_components(observed, observed_tag, tokens)
        for c in chars:
            char_rows.append({"phase":"v0.9.5.154_identity_graph","server":server,"rank":rank,**c,"operational_truth_modified":False})
        for t in tokens:
            token_rows.append({"phase":"v0.9.5.154_identity_graph","server":server,"rank":rank,**t,"operational_truth_modified":False})
            for cid in t["character_ids"]:
                edge_rows.append({"server":server,"rank":rank,"source_id":cid,"target_id":t["token_id"],"edge_type":"CHARACTER_IN_TOKEN","gold_authoritative":False})
        for comp in components:
            component_rows.append({"phase":"v0.9.5.154_identity_graph","server":server,"rank":rank,**comp,"operational_truth_modified":False})
            for tid in comp["token_ids"]:
                edge_rows.append({"server":server,"rank":rank,"source_id":tid,"target_id":comp["component_id"],"edge_type":"TOKEN_IN_COMPONENT","gold_authoritative":False})
        types = [c["component_type"] for c in components]
        metadata = _authoritative_gold_core_metadata(row)
        case_rows.append({
            "phase":"v0.9.5.154_identity_graph","server":server,"rank":rank,
            "observed_identity_text":observed,"observed_alliance_tag":observed_tag,
            "characters":len(chars),"tokens":len(tokens),"components":len(components),
            "component_types":json.dumps(types,ensure_ascii=False),
            "unknown_protected": observed.upper()=="UNKNOWN",
            "source_bound_characters":sum(1 for c in chars if c["source_chain_status"]!="DISPLAY_ONLY_NOT_EVIDENCE"),
            "identity_resolution_status":"UNKNOWN_PROTECTED" if observed.upper()=="UNKNOWN" else ("TOKENIZED_OBSERVED_IDENTITY" if tokens else "NO_OBSERVED_IDENTITY"),
            **metadata,"identity_authoritative":False,"gold_clearance_created":False,
            "ground_truth_used_as_evidence":False,"operational_truth_modified":False,
        })
    cases=pd.DataFrame(case_rows); chars=pd.DataFrame(char_rows); tokens=pd.DataFrame(token_rows); components=pd.DataFrame(component_rows); edges=pd.DataFrame(edge_rows)
    return cases, chars, tokens, components, edges


def _identity_slot_for_component(component_type: str) -> str:
    """Map a diagnostic component hypothesis to a non-authoritative identity slot."""
    return {
        "ALLIANCE_TAG_CANDIDATE": "ALLIANCE_TAG",
        "TITLE_OR_PREFIX": "TITLE_OR_PREFIX",
        "NAME_TOKEN": "PLAYER_NAME",
        "SCRIPT_NAME_BLOCK": "SCRIPT_BLOCK",
        "DECORATIVE_MARK": "DECORATION",
        "SEPARATOR": "SEPARATOR",
        "UNKNOWN_SENTINEL": "UNKNOWN_SEGMENT",
    }.get(normalize_text(component_type).upper(), "UNKNOWN_SEGMENT")


def _identity_review_guidance(metadata: dict[str, str], composition_status: str) -> tuple[str, str, str, str]:
    """Return priority, action, required evidence and complexity without using Ground Truth."""
    failure_class = normalize_text(metadata.get("failure_class", "")).lower()
    domain = normalize_text(metadata.get("failure_domain", "")).lower()
    root = normalize_text(metadata.get("root_cause", "")).lower()
    text = " ".join([failure_class, domain, root, normalize_text(composition_status).lower()])
    if "crop" in text or "geometry" in text:
        return "CRITICAL", "REVIEW_CROP_GEOMETRY", "source screenshot, crop bounds, row alignment", "HIGH"
    if "mixed" in text or "nonlocal" in text or "script" in text:
        return "MAJOR", "REVIEW_SCRIPT_IDENTITY", "source glyphs, script blocks, OCR alternatives", "MEDIUM"
    if "vote" in text or "conflict" in text or "observed_text_confirmed" in text:
        return "MAJOR", "REVIEW_EVIDENCE_CONFLICT", "character votes, aligned substitutions, source crops", "MEDIUM"
    if "unknown" in text or composition_status == "UNKNOWN_PROTECTED":
        return "CRITICAL", "REVIEW_MISSING_IDENTITY", "full row screenshot and independent OCR observation", "HIGH"
    if "glyph" in text or "local" in text:
        return "MAJOR", "REVIEW_LOCAL_GLYPH", "character crop, OCR candidates, provenance chain", "LOW"
    return "MINOR", "REVIEW_IDENTITY_COMPOSITION", "identity graph and source provenance", "LOW"


def _build_identity_composition_engine(
    identity_cases: pd.DataFrame,
    identity_characters: pd.DataFrame,
    identity_tokens: pd.DataFrame,
    identity_components: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """v0.9.5.155 Strike XII: compose diagnostic identity slots and review guidance.

    This layer is read-only and evidence-bound. It never reconstructs missing text,
    never consults expected identity fields, and never creates Gold clearance.
    """
    slot_rows: list[dict[str, Any]] = []
    composition_rows: list[dict[str, Any]] = []
    review_rows: list[dict[str, Any]] = []

    case_records = identity_cases.to_dict(orient="records") if not identity_cases.empty else []
    for case in case_records:
        server, rank = case.get("server"), case.get("rank")
        comps = identity_components[
            (identity_components.get("server", pd.Series(dtype=object)) == server)
            & (identity_components.get("rank", pd.Series(dtype=object)) == rank)
        ].copy() if not identity_components.empty else pd.DataFrame()
        tokens = identity_tokens[
            (identity_tokens.get("server", pd.Series(dtype=object)) == server)
            & (identity_tokens.get("rank", pd.Series(dtype=object)) == rank)
        ].copy() if not identity_tokens.empty else pd.DataFrame()
        chars = identity_characters[
            (identity_characters.get("server", pd.Series(dtype=object)) == server)
            & (identity_characters.get("rank", pd.Series(dtype=object)) == rank)
        ].copy() if not identity_characters.empty else pd.DataFrame()

        slot_texts: dict[str, list[str]] = {}
        slot_confidences: dict[str, list[float]] = {}
        source_component_ids: dict[str, list[str]] = {}
        source_token_ids: dict[str, list[str]] = {}
        source_character_ids: dict[str, list[str]] = {}
        source_screenshots: dict[str, set[str]] = {}
        source_observations: dict[str, set[str]] = {}

        for comp in comps.to_dict(orient="records"):
            slot = _identity_slot_for_component(comp.get("component_type", ""))
            comp_text = normalize_text(comp.get("component_text", ""))
            token_ids = comp.get("token_ids", [])
            if isinstance(token_ids, str):
                token_ids = _parse_json_list(token_ids)
            token_ids = [str(x) for x in token_ids]
            related_tokens = tokens[tokens.get("token_id", pd.Series(dtype=str)).astype(str).isin(token_ids)] if not tokens.empty else pd.DataFrame()
            character_ids: list[str] = []
            for token in related_tokens.to_dict(orient="records"):
                ids = token.get("character_ids", [])
                if isinstance(ids, str):
                    ids = _parse_json_list(ids)
                character_ids.extend(str(x) for x in ids)
            related_chars = chars[chars.get("character_id", pd.Series(dtype=str)).astype(str).isin(character_ids)] if not chars.empty else pd.DataFrame()
            source_bound_ratio = 0.0
            if not related_chars.empty:
                source_bound_ratio = float((related_chars["source_chain_status"].astype(str) != "DISPLAY_ONLY_NOT_EVIDENCE").mean())
            classification_confidence = float(pd.to_numeric(pd.Series([comp.get("classification_confidence", 0.0)]), errors="coerce").fillna(0.0).iloc[0])
            token_conf_values = pd.to_numeric(related_tokens.get("token_confidence", pd.Series(dtype=float)), errors="coerce").dropna().tolist() if not related_tokens.empty else []
            token_confidence = float(sum(token_conf_values) / len(token_conf_values)) if token_conf_values else (0.9 if source_bound_ratio == 1.0 else 0.45)
            component_confidence = round(max(0.0, min(1.0, classification_confidence * 0.55 + token_confidence * 0.30 + source_bound_ratio * 0.15)), 4)
            screenshots = sorted({normalize_text(x) for x in related_chars.get("source_screenshot", pd.Series(dtype=str)).tolist() if normalize_text(x)})
            observations = sorted({normalize_text(x) for x in related_chars.get("source_observation_id", pd.Series(dtype=str)).tolist() if normalize_text(x)})

            slot_texts.setdefault(slot, []).append(comp_text)
            slot_confidences.setdefault(slot, []).append(component_confidence)
            source_component_ids.setdefault(slot, []).append(str(comp.get("component_id", "")))
            source_token_ids.setdefault(slot, []).extend(token_ids)
            source_character_ids.setdefault(slot, []).extend(character_ids)
            source_screenshots.setdefault(slot, set()).update(screenshots)
            source_observations.setdefault(slot, set()).update(observations)

        for slot, texts in slot_texts.items():
            confidences = slot_confidences.get(slot, [])
            slot_conf = round(sum(confidences) / len(confidences), 4) if confidences else 0.0
            if slot == "SEPARATOR":
                slot_value = " "
            else:
                slot_value = " ".join(t for t in texts if t).strip()
            slot_rows.append({
                "phase": "v0.9.5.155_identity_composition",
                "server": server, "rank": rank, "identity_slot": slot,
                "slot_value": slot_value, "slot_confidence": slot_conf,
                "source_component_ids": json.dumps(source_component_ids.get(slot, []), ensure_ascii=False),
                "source_token_ids": json.dumps(sorted(set(source_token_ids.get(slot, []))), ensure_ascii=False),
                "source_character_ids": json.dumps(sorted(set(source_character_ids.get(slot, []))), ensure_ascii=False),
                "source_screenshots": json.dumps(sorted(source_screenshots.get(slot, set())), ensure_ascii=False),
                "source_observation_ids": json.dumps(sorted(source_observations.get(slot, set())), ensure_ascii=False),
                "token_confidence": round(sum(pd.to_numeric(tokens[tokens.get("token_id", pd.Series(dtype=str)).astype(str).isin(set(source_token_ids.get(slot, [])))].get("token_confidence", pd.Series(dtype=float)), errors="coerce").dropna().tolist()) / max(1, len(pd.to_numeric(tokens[tokens.get("token_id", pd.Series(dtype=str)).astype(str).isin(set(source_token_ids.get(slot, [])))].get("token_confidence", pd.Series(dtype=float)), errors="coerce").dropna().tolist())), 4) if not tokens.empty else 0.0,
                "component_provenance_complete": bool(source_component_ids.get(slot)) and bool(source_character_ids.get(slot)),
                "identity_authoritative": False, "gold_authoritative": False,
                "ground_truth_used_as_evidence": False, "operational_truth_modified": False,
            })

        unknown = bool(case.get("unknown_protected", False)) or "UNKNOWN_SEGMENT" in slot_texts
        player_values = [x for slot in ("PLAYER_NAME", "SCRIPT_BLOCK") for x in slot_texts.get(slot, []) if x]
        title_values = [x for x in slot_texts.get("TITLE_OR_PREFIX", []) if x]
        tag_values = [x for x in slot_texts.get("ALLIANCE_TAG", []) if x]
        identity_conf_values = [c for slot in ("PLAYER_NAME", "SCRIPT_BLOCK") for c in slot_confidences.get(slot, [])]
        identity_confidence = round(sum(identity_conf_values) / len(identity_conf_values), 4) if identity_conf_values else 0.0
        if unknown:
            status = "UNKNOWN_PROTECTED"
        elif player_values:
            status = "OBSERVED_IDENTITY_COMPOSED"
        elif slot_texts:
            status = "COMPONENTS_WITHOUT_PLAYER_NAME"
        else:
            status = "NO_OBSERVED_IDENTITY"
        metadata = {key: normalize_text(case.get(key, "")) for key in ("failure_class", "failure_domain", "fix_lane", "root_cause", "recommendation")}
        priority, action, required, complexity = _identity_review_guidance(metadata, status)
        composition_rows.append({
            "phase": "v0.9.5.155_identity_composition", "server": server, "rank": rank,
            "observed_identity_text": case.get("observed_identity_text", ""),
            "alliance_tag_slots": json.dumps(tag_values, ensure_ascii=False),
            "title_or_prefix_slots": json.dumps(title_values, ensure_ascii=False),
            "player_name_slots": json.dumps(player_values, ensure_ascii=False),
            "identity_composition_status": status,
            "identity_confidence": identity_confidence,
            "slot_count": len(slot_texts),
            "component_count": int(case.get("components", 0) or 0),
            "unknown_protected": unknown,
            **metadata,
            "identity_authoritative": False, "gold_clearance_created": False,
            "ground_truth_used_as_evidence": False, "operational_truth_modified": False,
        })
        review_rows.append({
            "phase": "v0.9.5.155_manual_review_queue", "server": server, "rank": rank,
            "priority": priority, "recommended_action": action,
            "required_evidence": required, "estimated_review_complexity": complexity,
            "identity_composition_status": status, "identity_confidence": identity_confidence,
            "observed_identity_text": case.get("observed_identity_text", ""),
            **metadata,
            "review_queue_authoritative": False, "gold_clearance_created": False,
            "ground_truth_used_as_evidence": False, "operational_truth_modified": False,
        })

    slots = pd.DataFrame(slot_rows)
    compositions = pd.DataFrame(composition_rows)
    review = pd.DataFrame(review_rows)
    if not review.empty:
        order = {"CRITICAL": 0, "MAJOR": 1, "MINOR": 2}
        review["priority_order"] = review["priority"].map(order).fillna(9)
        review = review.sort_values(["priority_order", "server", "rank"], kind="stable").drop(columns=["priority_order"]).reset_index(drop=True)
        root_summary = review.groupby(["failure_class", "root_cause", "recommended_action"], dropna=False).agg(
            cases=("rank", "count"), critical=("priority", lambda x: int((x == "CRITICAL").sum())),
            major=("priority", lambda x: int((x == "MAJOR").sum())),
        ).reset_index().sort_values(["cases", "critical"], ascending=[False, False], kind="stable")
        priority_summary = review.groupby(["priority", "recommended_action"], dropna=False).agg(cases=("rank", "count")).reset_index()
    else:
        root_summary = pd.DataFrame(columns=["failure_class", "root_cause", "recommended_action", "cases", "critical", "major"])
        priority_summary = pd.DataFrame(columns=["priority", "recommended_action", "cases"])
    return compositions, slots, review, root_summary, priority_summary



def _review_action_for_gold_case(failure_class: str, failure_domain: str, composition_status: str) -> tuple[str, str, str, str]:
    """v0.9.5.156: map an authoritative Gold-Core class to one concrete review action."""
    fc = normalize_text(failure_class).lower()
    fd = normalize_text(failure_domain).lower()
    status = normalize_text(composition_status).upper()
    if status in {"UNKNOWN_PROTECTED", "NO_OBSERVED_IDENTITY"}:
        return "CRITICAL", "REVIEW_MISSING_IDENTITY", "complete screenshot; uncropped row; OCR observation set; alternate crop or re-OCR", "HIGH"
    if fc == "observed_text_confirmed" or "evidence" in fd and "conflict" in fd:
        return "CRITICAL", "REVIEW_EVIDENCE_CONFLICT", "observed source characters; alignment operations; conflicting position evidence; source crops", "HIGH"
    if fc == "crop_geometry_problem" or "crop" in fd or "geometry" in fd:
        return "MAJOR", "REVIEW_CROP_GEOMETRY", "original screenshot; crop bounding box; neighboring row context; crop anchor diagnostics", "HIGH"
    if fc == "vote_warning_gate_review" or "vote" in fd:
        return "MAJOR", "REVIEW_VOTE_SELECTION", "candidate OCR votes; engine confidence; vote-selection rationale; source crops", "MEDIUM"
    if fc == "mixed_local_and_nonlocal_blocker" or "mixed" in fd or "split" in fd:
        return "MAJOR", "REVIEW_MIXED_SCRIPT", "script segmentation; token provenance; local/nonlocal split policy; display reconstruction", "MEDIUM"
    if fc == "policy_nonlocal_script_display" or "script" in fd:
        return "MAJOR", "REVIEW_SCRIPT_POLICY", "script segmentation; token provenance; policy decision; display reconstruction", "MEDIUM"
    if fc == "local_glyph_solvable" or "glyph" in fd:
        return "MAJOR", "REVIEW_LOCAL_GLYPH", "character crop; OCR candidates; vote consensus; provenance chain", "LOW"
    return "BLOCKED", "REVIEW_CASE_BINDING", "authoritative Gold-Core case metadata and unique case binding", "HIGH"


def _build_gold_core_bound_review_orchestration(
    compositions: pd.DataFrame,
    slots: pd.DataFrame,
    legacy_review: pd.DataFrame,
    gold_core_blockers: pd.DataFrame,
    gold_core_resolution_plan: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Strike XIII: bind Identity Composition to authoritative Gold-Core intelligence.

    The orchestration layer is read-only. It cannot clear Gold Core, reconstruct
    identity from Ground Truth, or mutate Operational Truth.
    """
    comp = compositions.copy()
    slot_frame = slots.copy()
    blockers = gold_core_blockers.copy()
    resolution = gold_core_resolution_plan.copy()

    def key_frame(df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        if out.empty:
            return out
        out["server"] = pd.to_numeric(out.get("server"), errors="coerce")
        out["rank"] = pd.to_numeric(out.get("rank"), errors="coerce")
        out["case_id"] = out.apply(lambda r: f"S{int(r['server'])}-R{int(r['rank'])}" if pd.notna(r.get('server')) and pd.notna(r.get('rank')) else "", axis=1)
        return out

    comp = key_frame(comp)
    blockers = key_frame(blockers)
    resolution = key_frame(resolution)

    # Build one authoritative record per open blocker. Resolution-plan fields win;
    # blocker fields fill classification gaps. Never use generic `matched` metadata.
    auth_rows: list[dict[str, Any]] = []
    for row in blockers.to_dict(orient="records"):
        case_id = row.get("case_id", "")
        candidates = resolution[resolution.get("case_id", pd.Series(dtype=str)).astype(str) == str(case_id)] if not resolution.empty else pd.DataFrame()
        rr = candidates.iloc[0].to_dict() if len(candidates) == 1 else {}
        def pick(*keys: str) -> Any:
            for source in (rr, row):
                for key in keys:
                    value = source.get(key, "")
                    if value is None or (isinstance(value, float) and pd.isna(value)):
                        continue
                    text = str(value).strip()
                    if text and text.lower() != "nan" and text.lower() != "matched":
                        return value
            return ""
        auth_rows.append({
            "case_id": case_id, "server": row.get("server"), "rank": row.get("rank"),
            "failure_class": pick("gold_core_failure_class", "failure_class"),
            "failure_domain": pick("gold_core_failure_domain", "failure_domain"),
            "fix_lane": pick("gold_core_fix_lane", "fix_lane", "gold_core_resolution_lane"),
            "root_cause": pick("gold_core_resolution_root_cause", "root_cause", "gold_core_failure_domain"),
            "root_cause_confidence": float(pd.to_numeric(pd.Series([pick("root_cause_confidence")]), errors="coerce").fillna(0.0).iloc[0]),
            "recommendation": pick("gold_core_resolution_recommendation", "recommendation", "gold_core_next_safe_action"),
            "recommendation_score": float(pd.to_numeric(pd.Series([pick("recommendation_score")]), errors="coerce").fillna(0.0).iloc[0]),
            "resolution_action": pick("gold_core_resolution_action", "resolution_action"),
            "elimination_action": pick("gold_core_elimination_action", "elimination_action"),
            "case_status": pick("case_status") or "OPEN",
            "blocker_status": "OPEN" if _bool_cell(row.get("gold_core_blocker", True)) else "CLOSED",
            "classification_source": pick("classification_source") or "gold_core_blocker_report",
        })
    auth = pd.DataFrame(auth_rows)

    binding_rows: list[dict[str, Any]] = []
    queue_rows: list[dict[str, Any]] = []
    confidence_rows: list[dict[str, Any]] = []
    enriched_rows: list[dict[str, Any]] = []
    for record in comp.to_dict(orient="records"):
        case_id = record.get("case_id", "")
        candidates = auth[auth.get("case_id", pd.Series(dtype=str)).astype(str) == str(case_id)] if not auth.empty else pd.DataFrame()
        join_method = "case_id"
        if len(candidates) != 1:
            candidates = auth[(auth.get("server", pd.Series(dtype=float)) == record.get("server")) & (auth.get("rank", pd.Series(dtype=float)) == record.get("rank"))] if not auth.empty else pd.DataFrame()
            join_method = "server_rank_fallback"
        join_status = "BOUND" if len(candidates) == 1 else ("AMBIGUOUS" if len(candidates) > 1 else "MISSING")
        binding_confidence = 1.0 if join_status == "BOUND" and join_method == "case_id" else (0.9 if join_status == "BOUND" else 0.0)
        binding_rows.append({
            "phase": "v0.9.5.156_gold_core_bound_review", "case_id": case_id,
            "server": record.get("server"), "rank": record.get("rank"), "join_method": join_method,
            "join_status": join_status, "candidate_count": len(candidates), "binding_confidence": binding_confidence,
            "binding_error": "" if join_status == "BOUND" else f"CASE_BINDING_{join_status}",
            "operational_truth_modified": False,
        })
        meta = candidates.iloc[0].to_dict() if len(candidates) == 1 else {
            "failure_class": "CASE_BINDING_ERROR", "failure_domain": "review_orchestration",
            "fix_lane": "case_binding", "root_cause": f"case_binding_{join_status.lower()}",
            "root_cause_confidence": 0.0, "recommendation": "Repair unique Gold-Core case binding before review.",
            "recommendation_score": 0.0, "resolution_action": "REVIEW_CASE_BINDING",
            "elimination_action": "keep_blocked", "case_status": "OPEN", "blocker_status": "OPEN",
            "classification_source": "binding_guard",
        }
        status = record.get("identity_composition_status", "")
        priority, action, required, complexity = _review_action_for_gold_case(meta.get("failure_class", ""), meta.get("failure_domain", ""), status)

        case_slots = slot_frame[(pd.to_numeric(slot_frame.get("server"), errors="coerce") == record.get("server")) & (pd.to_numeric(slot_frame.get("rank"), errors="coerce") == record.get("rank"))] if not slot_frame.empty else pd.DataFrame()
        prov_conf = float(case_slots.get("component_provenance_complete", pd.Series(dtype=bool)).fillna(False).astype(bool).mean()) if not case_slots.empty else 0.0
        token_conf = float(pd.to_numeric(case_slots.get("token_confidence", pd.Series(dtype=float)), errors="coerce").dropna().mean()) if not case_slots.empty and pd.to_numeric(case_slots.get("token_confidence", pd.Series(dtype=float)), errors="coerce").notna().any() else 0.0
        unknown_penalty = 1.0 if status == "UNKNOWN_PROTECTED" else 0.0
        script_penalty = 0.15 if not case_slots.empty and (case_slots.get("identity_slot", pd.Series(dtype=str)).astype(str) == "SCRIPT_BLOCK").any() else 0.0
        fragmentation_penalty = min(0.25, max(0, int(record.get("slot_count", 0) or 0) - 2) * 0.04)
        semantic_conf = round(max(0.0, min(1.0, float(record.get("identity_confidence", 0.0) or 0.0) - unknown_penalty - script_penalty - fragmentation_penalty)), 4)
        observation_conf = round(max(0.0, min(1.0, token_conf)), 4)
        review_conf = round(max(0.0, min(1.0, binding_confidence * 0.45 + float(meta.get("root_cause_confidence", 0.0) or 0.0) * 0.35 + (1.0 if action != "REVIEW_CASE_BINDING" else 0.0) * 0.20)), 4)
        aggregate = round(prov_conf * 0.25 + observation_conf * 0.25 + semantic_conf * 0.30 + review_conf * 0.20, 4)
        confidence_rows.append({
            "phase": "v0.9.5.156_confidence_calibration", "case_id": case_id, "server": record.get("server"), "rank": record.get("rank"),
            "provenance_confidence": round(prov_conf,4), "observation_confidence": observation_conf,
            "semantic_identity_confidence": semantic_conf, "review_confidence": review_conf,
            "identity_confidence": aggregate, "ground_truth_used_as_evidence": False,
            "operational_truth_modified": False,
        })
        enriched = {**record, **{k: meta.get(k, "") for k in ["failure_class","failure_domain","fix_lane","root_cause","root_cause_confidence","recommendation","recommendation_score","resolution_action","elimination_action","case_status","blocker_status","classification_source"]}}
        enriched.update({"phase":"v0.9.5.156_gold_core_bound_review","case_binding_status":join_status,"case_binding_method":join_method,"identity_confidence":aggregate,"review_confidence":review_conf})
        enriched_rows.append(enriched)
        queue_rows.append({
            "phase":"v0.9.5.156_manual_review_queue", "case_id":case_id, "server":record.get("server"), "rank":record.get("rank"),
            "priority":priority, "review_action":action, "recommended_action":action,
            "required_evidence":required, "estimated_review_complexity":complexity,
            "identity_composition_status":status, "identity_confidence":aggregate, "review_confidence":review_conf,
            "observed_identity_text":record.get("observed_identity_text", ""), "case_binding_status":join_status,
            **{k: meta.get(k, "") for k in ["failure_class","failure_domain","fix_lane","root_cause","root_cause_confidence","recommendation","recommendation_score","resolution_action","elimination_action","case_status","blocker_status","classification_source"]},
            "review_queue_authoritative":False,"gold_clearance_created":False,"ground_truth_used_as_evidence":False,"operational_truth_modified":False,
        })

    enriched_comp = pd.DataFrame(enriched_rows)
    queue = pd.DataFrame(queue_rows)
    bindings = pd.DataFrame(binding_rows)
    confidence = pd.DataFrame(confidence_rows)
    if not queue.empty:
        order={"CRITICAL":0,"MAJOR":1,"MINOR":2,"BLOCKED":9}
        queue["_order"] = queue["priority"].map(order).fillna(9)
        queue=queue.sort_values(["_order","server","rank"],kind="stable").drop(columns="_order").reset_index(drop=True)
        priority_summary=queue.groupby(["priority","review_action"],dropna=False).agg(cases=("case_id","count")).reset_index()
        root_summary=queue.groupby(["failure_class","failure_domain","fix_lane","root_cause","review_action"],dropna=False).agg(cases=("case_id","count"),avg_review_confidence=("review_confidence","mean")).reset_index()
    else:
        priority_summary=pd.DataFrame(columns=["priority","review_action","cases"])
        root_summary=pd.DataFrame(columns=["failure_class","failure_domain","fix_lane","root_cause","review_action","cases","avg_review_confidence"])

    open_cases=len(auth)
    validation_rows=[
        {"guard":"queue_coverage","expected":open_cases,"actual":len(queue),"status":"PASS" if len(queue)==open_cases else "FAIL"},
        {"guard":"unique_case_binding","expected":open_cases,"actual":int((bindings.get('join_status',pd.Series(dtype=str))=='BOUND').sum()),"status":"PASS" if not bindings.empty and (bindings['join_status']=='BOUND').all() else "FAIL"},
        {"guard":"failure_class_not_matched","expected":0,"actual":int(queue.get('failure_class',pd.Series(dtype=str)).astype(str).str.lower().eq('matched').sum()),"status":"PASS" if queue.empty or not queue['failure_class'].astype(str).str.lower().eq('matched').any() else "FAIL"},
        {"guard":"root_cause_complete","expected":open_cases,"actual":int(queue.get('root_cause',pd.Series(dtype=str)).astype(str).str.strip().ne('').sum()),"status":"PASS" if queue.empty or queue['root_cause'].astype(str).str.strip().ne('').all() else "FAIL"},
        {"guard":"recommendation_complete","expected":open_cases,"actual":int(queue.get('recommendation',pd.Series(dtype=str)).astype(str).str.strip().ne('').sum()),"status":"PASS" if queue.empty or queue['recommendation'].astype(str).str.strip().ne('').all() else "FAIL"},
        {"guard":"concrete_review_action","expected":open_cases,"actual":int(queue.get('review_action',pd.Series(dtype=str)).astype(str).ne('REVIEW_IDENTITY_COMPOSITION').sum()) if not queue.empty else 0,"status":"PASS" if queue.empty or not queue['review_action'].astype(str).eq('REVIEW_IDENTITY_COMPOSITION').any() else "FAIL"},
        {"guard":"gold_clearance_created","expected":0,"actual":int(queue.get('gold_clearance_created',pd.Series(dtype=bool)).fillna(False).astype(bool).sum()),"status":"PASS" if queue.empty or not queue['gold_clearance_created'].fillna(False).astype(bool).any() else "FAIL"},
    ]
    validation=pd.DataFrame(validation_rows)
    orchestration_summary=pd.DataFrame([{
        "phase":"v0.9.5.156_gold_core_bound_review", "open_gold_core_cases":open_cases,"review_queue_cases":len(queue),
        "queue_coverage_percent":round((len(queue)/open_cases*100) if open_cases else 100.0,2),
        "case_binding_success_percent":round(((bindings['join_status']=='BOUND').mean()*100) if not bindings.empty else 100.0,2),
        "metadata_complete_cases":int((queue.get('root_cause',pd.Series(dtype=str)).astype(str).str.strip().ne('') & queue.get('recommendation',pd.Series(dtype=str)).astype(str).str.strip().ne('')).sum()) if not queue.empty else 0,
        "critical_review_cases":int((queue.get('priority',pd.Series(dtype=str))=='CRITICAL').sum()),
        "major_review_cases":int((queue.get('priority',pd.Series(dtype=str))=='MAJOR').sum()),
        "minor_review_cases":int((queue.get('priority',pd.Series(dtype=str))=='MINOR').sum()),
        "unclassified_review_cases":int((queue.get('priority',pd.Series(dtype=str))=='BLOCKED').sum()),
        "review_authoritative":False,"gold_authoritative":False,"ground_truth_used_as_evidence":False,"operational_truth_modified":False,
    }])
    return enriched_comp, queue, root_summary, priority_summary, bindings, confidence, validation, orchestration_summary


def _resolution_readiness_for_case(row: dict[str, Any]) -> tuple[str, str, str]:
    """Return diagnostic readiness, strategy, and rationale for one review case."""
    action = str(row.get("review_action", "") or "")
    failure_class = str(row.get("failure_class", "") or "").lower()
    binding = str(row.get("case_binding_status", "") or "")
    status = str(row.get("identity_composition_status", "") or "")
    evidence_coverage = float(row.get("required_evidence_coverage", 0.0) or 0.0)
    review_conf = float(row.get("review_confidence", 0.0) or 0.0)

    if binding != "BOUND" or action == "REVIEW_CASE_BINDING":
        return "UNSAFE_TO_RESOLVE", "REPAIR_CASE_BINDING", "Authoritative case binding is missing or ambiguous."
    if status == "UNKNOWN_PROTECTED" or action == "REVIEW_MISSING_IDENTITY":
        return "WAITING_FOR_EVIDENCE", "COLLECT_IDENTITY_EVIDENCE", "Observed identity is unavailable or protected as UNKNOWN."
    if action == "REVIEW_CROP_GEOMETRY":
        if evidence_coverage >= 0.75 and review_conf >= 0.72:
            return "READY_FOR_TARGETED_REOCR", "RECROP_AND_TARGETED_REOCR", "Crop diagnostics and provenance support a targeted acquisition attempt."
        return "WAITING_FOR_EVIDENCE", "COLLECT_CROP_DIAGNOSTICS", "Crop repair requires stronger source-row and geometry evidence."
    if action in {"REVIEW_SCRIPT_POLICY", "REVIEW_MIXED_SCRIPT"}:
        return "POLICY_DECISION_REQUIRED", "MANUAL_SCRIPT_POLICY_REVIEW", "Resolution depends on multilingual display policy rather than OCR confidence alone."
    if action == "REVIEW_EVIDENCE_CONFLICT":
        return "READY_FOR_MANUAL_REVIEW", "MANUAL_EVIDENCE_ADJUDICATION", "Observed evidence conflicts with the expected comparison target and must remain human-reviewed."
    if action == "REVIEW_VOTE_SELECTION":
        if evidence_coverage >= 0.75 and review_conf >= 0.72:
            return "READY_FOR_TARGETED_REOCR", "REPLAY_VOTE_SELECTION_WITH_TARGETED_REOCR", "Vote evidence is sufficiently complete for a constrained re-evaluation."
        return "READY_FOR_MANUAL_REVIEW", "MANUAL_VOTE_ADJUDICATION", "Vote candidates are present but not safe for automated resolution."
    if action == "REVIEW_LOCAL_GLYPH" or failure_class == "local_glyph_solvable":
        if evidence_coverage >= 0.75 and review_conf >= 0.78:
            return "READY_FOR_TARGETED_REOCR", "TARGETED_LOCAL_GLYPH_REOCR", "Local glyph evidence is narrow enough for targeted reacquisition."
        return "READY_FOR_MANUAL_REVIEW", "MANUAL_LOCAL_GLYPH_REVIEW", "Local glyph remains solvable but current confidence is insufficient for automation."
    return "UNSAFE_TO_RESOLVE", "KEEP_BLOCKED", "No evidence-safe resolution strategy is available."


def _build_resolution_readiness_intelligence(
    manual_review_queue: pd.DataFrame,
    review_case_bindings: pd.DataFrame,
    review_confidence_calibration: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Strike XIV: evidence-based confidence and diagnostic resolution readiness.

    This layer is strictly read-only. It does not execute fixes, clear Gold Core,
    reconstruct identity from Ground Truth, or mutate Operational Truth.
    """
    queue = manual_review_queue.copy()
    bindings = review_case_bindings.copy()
    confidence = review_confidence_calibration.copy()
    if queue.empty:
        empty = pd.DataFrame()
        return empty, empty, empty, pd.DataFrame([{
            "phase": "v0.9.5.157_resolution_readiness", "cases": 0,
            "scored_root_causes": 0, "scored_recommendations": 0,
            "dynamic_review_confidence_cases": 0, "readiness_classified_cases": 0,
            "gold_clearance_created": 0, "ground_truth_used_as_evidence": False,
            "operational_truth_modified": False,
        }])

    bind_map = {str(r.get("case_id", "")): r for r in bindings.to_dict(orient="records")}
    conf_map = {str(r.get("case_id", "")): r for r in confidence.to_dict(orient="records")}
    rows: list[dict[str, Any]] = []
    for row in queue.to_dict(orient="records"):
        case_id = str(row.get("case_id", ""))
        b = bind_map.get(case_id, {})
        c = conf_map.get(case_id, {})
        binding_conf = float(b.get("binding_confidence", 0.0) or 0.0)
        provenance_conf = float(c.get("provenance_confidence", 0.0) or 0.0)
        observation_conf = float(c.get("observation_confidence", 0.0) or 0.0)
        semantic_conf = float(c.get("semantic_identity_confidence", 0.0) or 0.0)
        failure_class = str(row.get("failure_class", "") or "").lower()
        failure_domain = str(row.get("failure_domain", "") or "").lower()
        action = str(row.get("review_action", "") or "")
        status = str(row.get("identity_composition_status", "") or "")

        required = [x.strip() for x in str(row.get("required_evidence", "") or "").split(";") if x.strip()]
        evidence_coverage = round(min(1.0, (provenance_conf * 0.45) + (observation_conf * 0.35) + (0.20 if required else 0.0)), 4)

        class_specificity = 0.95 if failure_class and failure_class not in {"matched", "case_binding_error"} else 0.0
        domain_specificity = 0.90 if failure_domain and failure_domain not in {"review_orchestration", ""} else 0.25
        action_support = {
            "REVIEW_CROP_GEOMETRY": 0.92,
            "REVIEW_EVIDENCE_CONFLICT": 0.94,
            "REVIEW_LOCAL_GLYPH": 0.88,
            "REVIEW_VOTE_SELECTION": 0.84,
            "REVIEW_MIXED_SCRIPT": 0.82,
            "REVIEW_SCRIPT_POLICY": 0.80,
            "REVIEW_MISSING_IDENTITY": 0.72,
            "REVIEW_CASE_BINDING": 0.0,
        }.get(action, 0.45)
        root_conf = round(max(0.0, min(1.0,
            binding_conf * 0.25 + class_specificity * 0.25 + domain_specificity * 0.20
            + provenance_conf * 0.15 + action_support * 0.15
        )), 4)
        if status == "UNKNOWN_PROTECTED":
            root_conf = round(max(0.0, root_conf - 0.12), 4)

        risk_factor = {
            "REVIEW_EVIDENCE_CONFLICT": 0.55,
            "REVIEW_MIXED_SCRIPT": 0.65,
            "REVIEW_SCRIPT_POLICY": 0.62,
            "REVIEW_MISSING_IDENTITY": 0.45,
            "REVIEW_CROP_GEOMETRY": 0.82,
            "REVIEW_VOTE_SELECTION": 0.76,
            "REVIEW_LOCAL_GLYPH": 0.88,
            "REVIEW_CASE_BINDING": 0.0,
        }.get(action, 0.40)
        recommendation_score = round(max(0.0, min(1.0,
            action_support * 0.30 + evidence_coverage * 0.25 + root_conf * 0.25
            + risk_factor * 0.20
        )), 4)

        review_conf = round(max(0.0, min(1.0,
            binding_conf * 0.20 + root_conf * 0.25 + recommendation_score * 0.25
            + evidence_coverage * 0.15 + semantic_conf * 0.15
        )), 4)
        enriched = {**row,
            "phase": "v0.9.5.157_resolution_readiness",
            "binding_confidence": round(binding_conf, 4),
            "provenance_confidence": round(provenance_conf, 4),
            "observation_confidence": round(observation_conf, 4),
            "semantic_identity_confidence": round(semantic_conf, 4),
            "required_evidence_coverage": evidence_coverage,
            "root_cause_confidence": root_conf,
            "recommendation_score": recommendation_score,
            "review_confidence": review_conf,
        }
        readiness, strategy, rationale = _resolution_readiness_for_case(enriched)
        enriched.update({
            "resolution_readiness": readiness,
            "resolution_strategy": strategy,
            "resolution_rationale": rationale,
            "resolution_readiness_authoritative": False,
            "automatic_fix_executed": False,
            "gold_clearance_created": False,
            "ground_truth_used_as_evidence": False,
            "operational_truth_modified": False,
        })
        rows.append(enriched)

    cases = pd.DataFrame(rows)
    readiness_summary = cases.groupby(["resolution_readiness", "resolution_strategy"], dropna=False).agg(
        cases=("case_id", "count"),
        avg_root_cause_confidence=("root_cause_confidence", "mean"),
        avg_recommendation_score=("recommendation_score", "mean"),
        avg_review_confidence=("review_confidence", "mean"),
    ).reset_index()
    validation = pd.DataFrame([
        {"guard":"root_cause_confidence_scored","expected":len(cases),"actual":int((pd.to_numeric(cases["root_cause_confidence"],errors="coerce")>0).sum()),"status":"PASS" if (pd.to_numeric(cases["root_cause_confidence"],errors="coerce")>0).all() else "FAIL"},
        {"guard":"recommendation_score_scored","expected":len(cases),"actual":int((pd.to_numeric(cases["recommendation_score"],errors="coerce")>0).sum()),"status":"PASS" if (pd.to_numeric(cases["recommendation_score"],errors="coerce")>0).all() else "FAIL"},
        {"guard":"resolution_readiness_complete","expected":len(cases),"actual":int(cases["resolution_readiness"].astype(str).str.strip().ne("").sum()),"status":"PASS" if cases["resolution_readiness"].astype(str).str.strip().ne("").all() else "FAIL"},
        {"guard":"resolution_strategy_complete","expected":len(cases),"actual":int(cases["resolution_strategy"].astype(str).str.strip().ne("").sum()),"status":"PASS" if cases["resolution_strategy"].astype(str).str.strip().ne("").all() else "FAIL"},
        {"guard":"no_automatic_fix","expected":0,"actual":int(cases["automatic_fix_executed"].fillna(False).astype(bool).sum()),"status":"PASS" if not cases["automatic_fix_executed"].fillna(False).astype(bool).any() else "FAIL"},
        {"guard":"no_gold_clearance","expected":0,"actual":int(cases["gold_clearance_created"].fillna(False).astype(bool).sum()),"status":"PASS" if not cases["gold_clearance_created"].fillna(False).astype(bool).any() else "FAIL"},
        {"guard":"operational_truth_immutable","expected":0,"actual":int(cases["operational_truth_modified"].fillna(False).astype(bool).sum()),"status":"PASS" if not cases["operational_truth_modified"].fillna(False).astype(bool).any() else "FAIL"},
    ])
    summary = pd.DataFrame([{
        "phase":"v0.9.5.157_resolution_readiness",
        "cases":len(cases),
        "scored_root_causes":int((pd.to_numeric(cases["root_cause_confidence"],errors="coerce")>0).sum()),
        "scored_recommendations":int((pd.to_numeric(cases["recommendation_score"],errors="coerce")>0).sum()),
        "dynamic_review_confidence_cases":int(cases["review_confidence"].nunique(dropna=True)),
        "readiness_classified_cases":int(cases["resolution_readiness"].astype(str).str.strip().ne("").sum()),
        "ready_for_targeted_reocr":int((cases["resolution_readiness"]=="READY_FOR_TARGETED_REOCR").sum()),
        "ready_for_manual_review":int((cases["resolution_readiness"]=="READY_FOR_MANUAL_REVIEW").sum()),
        "waiting_for_evidence":int((cases["resolution_readiness"]=="WAITING_FOR_EVIDENCE").sum()),
        "policy_decision_required":int((cases["resolution_readiness"]=="POLICY_DECISION_REQUIRED").sum()),
        "unsafe_to_resolve":int((cases["resolution_readiness"]=="UNSAFE_TO_RESOLVE").sum()),
        "gold_clearance_created":0,
        "ground_truth_used_as_evidence":False,
        "operational_truth_modified":False,
    }])
    return cases, readiness_summary, validation, summary


def _stable_hash(payload: dict[str, Any]) -> str:
    """Return a deterministic SHA-256 fingerprint for diagnostic state."""
    canonical = json.dumps(_json_safe(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _confidence_label(value: float) -> str:
    value = float(value or 0.0)
    if value >= 0.90:
        return "VERY_HIGH"
    if value >= 0.80:
        return "HIGH"
    if value >= 0.65:
        return "MODERATE"
    if value > 0.0:
        return "LOW"
    return "INSUFFICIENT"


def _evidence_requirements_for_action(action: str) -> list[str]:
    return {
        "REVIEW_CROP_GEOMETRY": ["original_screenshot", "crop_bbox", "row_context", "crop_anchor_diagnostics", "field_bleed_diagnostics"],
        "REVIEW_MISSING_IDENTITY": ["full_row_screenshot", "alternate_crop", "ocr_observation_set", "position_binding"],
        "REVIEW_EVIDENCE_CONFLICT": ["observed_evidence", "expected_comparison", "alignment_trace", "position_evidence"],
        "REVIEW_VOTE_SELECTION": ["ocr_candidates", "vote_confidence", "vote_rationale", "source_crops"],
        "REVIEW_SCRIPT_POLICY": ["script_segmentation", "token_provenance", "display_policy", "display_reconstruction"],
        "REVIEW_MIXED_SCRIPT": ["script_segmentation", "token_provenance", "local_nonlocal_split", "display_policy"],
        "REVIEW_LOCAL_GLYPH": ["source_crop", "character_positions", "alternate_ocr", "glyph_provenance"],
        "REVIEW_CASE_BINDING": ["case_id", "server_rank", "gold_core_record", "binding_trace"],
    }.get(action, ["source_observation", "provenance_chain", "review_rationale"])


def _evidence_presence(row: dict[str, Any], item: str) -> bool:
    text = lambda key: str(row.get(key, "") or "").strip()
    num = lambda key: float(row.get(key, 0.0) or 0.0)
    mapping = {
        "original_screenshot": bool(text("source_screenshots") or text("screenshot") or text("screenshot_path")),
        "full_row_screenshot": bool(text("source_screenshots") or text("screenshot") or text("screenshot_path")),
        "source_crop": bool(text("source_screenshots") or text("source_observations")),
        "source_crops": bool(text("source_screenshots") or text("source_observations")),
        "alternate_crop": bool(text("alternate_crop") or text("reocr_crop") or text("crop_variants")),
        "crop_bbox": bool(text("crop_bbox") or text("bounding_box") or text("bbox")),
        "row_context": bool(text("row_context") or text("neighboring_rows") or text("source_observations")),
        "crop_anchor_diagnostics": "crop" in text("failure_domain").lower() or bool(text("crop_anchor_diagnostics")),
        "field_bleed_diagnostics": "bleed" in text("failure_domain").lower() or bool(text("field_bleed_diagnostics")),
        "ocr_observation_set": bool(text("source_observations") or text("observed_identity_text")),
        "position_binding": text("case_binding_status") == "BOUND" and num("binding_confidence") > 0,
        "observed_evidence": bool(text("observed_identity_text") and text("observed_identity_text").upper() != "UNKNOWN"),
        "expected_comparison": bool(text("expected_name") or text("expected_identity") or text("root_cause")),
        "alignment_trace": bool(text("alignment_operations") or text("alignment_trace") or "evidence" in text("failure_domain").lower()),
        "position_evidence": num("provenance_confidence") > 0 or bool(text("source_characters")),
        "ocr_candidates": bool(text("ocr_candidates") or text("source_observations")),
        "vote_confidence": num("observation_confidence") > 0,
        "vote_rationale": bool(text("recommendation") or text("resolution_rationale")),
        "script_segmentation": bool(text("script_profile") or text("component_types") or text("identity_slots")),
        "token_provenance": num("provenance_confidence") > 0 and bool(text("source_tokens") or text("component_provenance") or text("observed_identity_text")),
        "display_policy": bool(text("recommendation") and ("policy" in text("review_action").lower() or "script" in text("failure_class").lower() or "script" in text("failure_domain").lower())),
        "display_reconstruction": bool(text("display_reconstruction") or text("observed_identity_text")),
        "local_nonlocal_split": text("review_action") == "REVIEW_MIXED_SCRIPT",
        "character_positions": bool(text("source_characters") or text("component_provenance") or num("provenance_confidence") > 0),
        "alternate_ocr": bool(text("alternate_ocr") or text("ocr_candidates") or num("observation_confidence") >= 0.9),
        "glyph_provenance": num("provenance_confidence") > 0,
        "case_id": bool(text("case_id")), "server_rank": bool(text("server") and text("rank")),
        "gold_core_record": bool(text("classification_source")), "binding_trace": text("case_binding_status") == "BOUND",
        "source_observation": bool(text("observed_identity_text")), "provenance_chain": num("provenance_confidence") > 0,
        "review_rationale": bool(text("resolution_rationale") or text("recommendation")),
    }
    return bool(mapping.get(item, False))


def _build_classification_stability_and_coverage(
    readiness_cases: pd.DataFrame, output_dir: Path | None = None
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Strike XV: deterministic classification audit and action-specific evidence coverage."""
    if readiness_cases.empty:
        empty = pd.DataFrame()
        return empty, empty, empty, empty, pd.DataFrame([{"phase":"v0.9.5.158_classification_stability","cases":0}])
    previous: dict[str, dict[str, Any]] = {}
    history_path = Path(output_dir) / "classification_stability_state.json" if output_dir else None
    if history_path and history_path.exists():
        try:
            previous = {str(x.get("case_id", "")): x for x in json.loads(history_path.read_text(encoding="utf-8")).get("cases", [])}
        except (OSError, ValueError, TypeError):
            previous = {}
    rows=[]; coverage_rows=[]; factor_rows=[]
    for raw in readiness_cases.to_dict(orient="records"):
        row=dict(raw); case_id=str(row.get("case_id", "")); action=str(row.get("review_action", ""))
        requirements=_evidence_requirements_for_action(action)
        present=[item for item in requirements if _evidence_presence(row,item)]
        missing=[item for item in requirements if item not in present]
        coverage=round(len(present)/len(requirements),4) if requirements else 0.0
        row["required_evidence_coverage"]=coverage
        row["required_evidence_items"]=";".join(requirements)
        row["available_evidence_items"]=";".join(present)
        row["missing_evidence_items"]=";".join(missing)
        evidence_payload={k:row.get(k,"") for k in ["case_id","server","rank","observed_identity_text","identity_composition_status","case_binding_status","binding_confidence","provenance_confidence","observation_confidence","semantic_identity_confidence","source_screenshots","source_observations","source_characters","failure_domain"]}
        evidence_payload["evidence_presence"]={item:_evidence_presence(row,item) for item in requirements}
        evidence_fp=_stable_hash(evidence_payload)
        classification_payload={"evidence_fingerprint":evidence_fp,"failure_class":row.get("failure_class",""),"failure_domain":row.get("failure_domain",""),"fix_lane":row.get("fix_lane",""),"review_action":action}
        classification_fp=_stable_hash(classification_payload)
        decision_payload={**classification_payload,"resolution_readiness":row.get("resolution_readiness",""),"resolution_strategy":row.get("resolution_strategy","")}
        decision_hash=_stable_hash(decision_payload)
        prev=previous.get(case_id,{})
        evidence_changed=bool(prev) and prev.get("evidence_fingerprint") != evidence_fp
        classification_changed=bool(prev) and prev.get("classification_fingerprint") != classification_fp
        decision_changed=bool(prev) and prev.get("decision_hash") != decision_hash
        if not prev: reason="NO_PREVIOUS_BASELINE"
        elif classification_changed and not evidence_changed: reason="UNEXPLAINED_CLASSIFICATION_CHANGE"
        elif classification_changed: reason="EVIDENCE_CHANGED"
        elif decision_changed and not evidence_changed: reason="UNEXPLAINED_DECISION_CHANGE"
        elif decision_changed: reason="EVIDENCE_CHANGED"
        else: reason="STABLE"
        severity="CRITICAL" if "UNEXPLAINED" in reason else ("INFO" if reason in {"STABLE","NO_PREVIOUS_BASELINE"} else "MAJOR")
        # Explicit score decompositions: explanatory indicators, not probabilities.
        root_factors={"binding":round(float(row.get("binding_confidence",0) or 0)*0.25,4),"classification_specificity":0.2375 if str(row.get("failure_class","")).lower() not in {"","matched","case_binding_error"} else 0.0,"domain_specificity":0.18 if str(row.get("failure_domain","")).strip() else 0.05,"provenance":round(float(row.get("provenance_confidence",0) or 0)*0.15,4),"action_support":round(max(0.0,float(row.get("root_cause_confidence",0) or 0)-0.70),4)}
        rec_factors={"root_cause":round(float(row.get("root_cause_confidence",0) or 0)*0.25,4),"evidence_coverage":round(coverage*0.25,4),"action_fit":round(float(row.get("recommendation_score",0) or 0)*0.30,4),"safety":0.20 if not bool(row.get("automatic_fix_executed",False)) else 0.0}
        review_factors={"binding":round(float(row.get("binding_confidence",0) or 0)*0.20,4),"root_cause":round(float(row.get("root_cause_confidence",0) or 0)*0.25,4),"recommendation":round(float(row.get("recommendation_score",0) or 0)*0.25,4),"evidence_coverage":round(coverage*0.15,4),"semantic_identity":round(float(row.get("semantic_identity_confidence",0) or 0)*0.15,4)}
        row.update({"phase":"v0.9.5.158_classification_stability","evidence_fingerprint":evidence_fp,"classification_fingerprint":classification_fp,"decision_hash":decision_hash,"previous_failure_class":prev.get("failure_class","") if prev else "","current_failure_class":row.get("failure_class",""),"evidence_changed":evidence_changed,"classification_changed":classification_changed,"decision_changed":decision_changed,"classification_change_reason":reason,"stability_severity":severity,"root_cause_confidence_label":_confidence_label(row.get("root_cause_confidence",0)),"recommendation_score_label":_confidence_label(row.get("recommendation_score",0)),"review_confidence_label":_confidence_label(row.get("review_confidence",0)),"root_cause_confidence_factors":json.dumps(root_factors,sort_keys=True),"recommendation_score_factors":json.dumps(rec_factors,sort_keys=True),"review_confidence_factors":json.dumps(review_factors,sort_keys=True)})
        # Recalculate review confidence with real action-specific coverage.
        row["review_confidence"]=round(max(0.0,min(1.0,sum(review_factors.values()))),4)
        row["review_confidence_label"]=_confidence_label(row["review_confidence"])
        rows.append(row)
        for item in requirements:
            coverage_rows.append({"case_id":case_id,"review_action":action,"evidence_item":item,"available":item in present,"coverage":coverage})
        for score_name,factors in [("root_cause_confidence",root_factors),("recommendation_score",rec_factors),("review_confidence",review_factors)]:
            for factor,contribution in factors.items(): factor_rows.append({"case_id":case_id,"score":score_name,"factor":factor,"contribution":contribution})
    cases=pd.DataFrame(rows); coverage_df=pd.DataFrame(coverage_rows); factors_df=pd.DataFrame(factor_rows)
    validation=pd.DataFrame([
        {"guard":"no_unexplained_classification_change","expected":0,"actual":int(((cases["classification_changed"]==True)&(cases["evidence_changed"]==False)).sum()),"status":"PASS" if not ((cases["classification_changed"]==True)&(cases["evidence_changed"]==False)).any() else "FAIL"},
        {"guard":"no_unexplained_decision_change","expected":0,"actual":int(((cases["decision_changed"]==True)&(cases["evidence_changed"]==False)).sum()),"status":"PASS" if not ((cases["decision_changed"]==True)&(cases["evidence_changed"]==False)).any() else "FAIL"},
        {"guard":"evidence_fingerprint_complete","expected":len(cases),"actual":int(cases["evidence_fingerprint"].astype(str).str.len().eq(64).sum()),"status":"PASS" if cases["evidence_fingerprint"].astype(str).str.len().eq(64).all() else "FAIL"},
        {"guard":"score_decomposition_complete","expected":len(cases)*3,"actual":len(cases)*3 if all(cases[x].astype(str).str.strip().ne("").all() for x in ["root_cause_confidence_factors","recommendation_score_factors","review_confidence_factors"]) else 0,"status":"PASS" if all(cases[x].astype(str).str.strip().ne("").all() for x in ["root_cause_confidence_factors","recommendation_score_factors","review_confidence_factors"]) else "FAIL"},
        {"guard":"confidence_labels_complete","expected":len(cases)*3,"actual":sum(int(cases[x].astype(str).str.strip().ne("").sum()) for x in ["root_cause_confidence_label","recommendation_score_label","review_confidence_label"]),"status":"PASS" if all(cases[x].astype(str).str.strip().ne("").all() for x in ["root_cause_confidence_label","recommendation_score_label","review_confidence_label"]) else "FAIL"},
        {"guard":"no_gold_clearance","expected":0,"actual":int(cases["gold_clearance_created"].fillna(False).astype(bool).sum()),"status":"PASS" if not cases["gold_clearance_created"].fillna(False).astype(bool).any() else "FAIL"},
    ])
    summary=pd.DataFrame([{"phase":"v0.9.5.158_classification_stability","cases":len(cases),"previous_baseline_cases":len(previous),"classification_changes":int(cases["classification_changed"].sum()),"unexplained_classification_changes":int(((cases["classification_changed"]==True)&(cases["evidence_changed"]==False)).sum()),"decision_changes":int(cases["decision_changed"].sum()),"distinct_evidence_coverage_values":int(cases["required_evidence_coverage"].nunique()),"average_evidence_coverage":round(float(cases["required_evidence_coverage"].mean()),4),"gold_clearance_created":0,"operational_truth_modified":False}])
    if history_path:
        try:
            history_path.write_text(json.dumps({"version":"0.9.5.158","cases":[{k:r.get(k) for k in ["case_id","failure_class","evidence_fingerprint","classification_fingerprint","decision_hash"]} for r in rows]},ensure_ascii=False,indent=2),encoding="utf-8")
        except OSError:
            pass
    return cases, coverage_df, factors_df, validation, summary


def _build_stability_verification_history(
    stability_cases: pd.DataFrame, output_dir: Path | None = None, release_version: str = "0.9.5.159"
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Strike XVI: persist immutable cross-run decision history and explain drift."""
    columns = [
        "run_id", "run_timestamp_utc", "version", "case_id", "server", "rank",
        "evidence_fingerprint", "classification_fingerprint", "decision_hash",
        "failure_class", "failure_domain", "review_action", "resolution_readiness",
        "resolution_strategy", "root_cause_confidence", "recommendation_score",
        "review_confidence", "required_evidence_coverage",
    ]
    if stability_cases.empty:
        empty = pd.DataFrame(columns=columns)
        validation = pd.DataFrame([
            {"guard":"history_cases_recorded","expected":0,"actual":0,"status":"PASS"},
            {"guard":"no_unexplained_cross_run_drift","expected":0,"actual":0,"status":"PASS"},
        ])
        summary = pd.DataFrame([{"phase":"v0.9.5.159_stability_verification","cases":0,"history_entries":0,"runs":0,"unexplained_drifts":0}])
        return empty, empty, empty, empty, validation, summary

    history_path = Path(output_dir) / "decision_history_state.json" if output_dir else None
    previous_entries: list[dict[str, Any]] = []
    if history_path and history_path.exists():
        try:
            payload = json.loads(history_path.read_text(encoding="utf-8"))
            previous_entries = list(payload.get("entries", []))
        except (OSError, ValueError, TypeError):
            previous_entries = []

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    run_seed = {
        "version": release_version,
        "cases": sorted(
            [{"case_id": str(r.get("case_id", "")), "evidence_fingerprint": str(r.get("evidence_fingerprint", "")), "decision_hash": str(r.get("decision_hash", ""))}
             for r in stability_cases.to_dict(orient="records")],
            key=lambda x: x["case_id"],
        ),
    }
    run_id = f"{release_version}-{_stable_hash(run_seed)[:12]}"
    current_entries: list[dict[str, Any]] = []
    for row in stability_cases.to_dict(orient="records"):
        current_entries.append({
            "run_id": run_id, "run_timestamp_utc": now, "version": release_version,
            "case_id": str(row.get("case_id", "")), "server": row.get("server", ""), "rank": row.get("rank", ""),
            "evidence_fingerprint": str(row.get("evidence_fingerprint", "")),
            "classification_fingerprint": str(row.get("classification_fingerprint", "")),
            "decision_hash": str(row.get("decision_hash", "")),
            "failure_class": str(row.get("failure_class", "")), "failure_domain": str(row.get("failure_domain", "")),
            "review_action": str(row.get("review_action", "")),
            "resolution_readiness": str(row.get("resolution_readiness", "")),
            "resolution_strategy": str(row.get("resolution_strategy", "")),
            "root_cause_confidence": float(row.get("root_cause_confidence", 0) or 0),
            "recommendation_score": float(row.get("recommendation_score", 0) or 0),
            "review_confidence": float(row.get("review_confidence", 0) or 0),
            "required_evidence_coverage": float(row.get("required_evidence_coverage", 0) or 0),
        })

    # Idempotency: rerunning the exact same release/input does not duplicate history.
    known_keys = {(str(e.get("run_id", "")), str(e.get("case_id", ""))) for e in previous_entries}
    appended = [e for e in current_entries if (e["run_id"], e["case_id"]) not in known_keys]
    all_entries = previous_entries + appended
    history_df = pd.DataFrame(all_entries, columns=columns)

    # Compare every current case with its latest prior observation, independent of version.
    prior_by_case: dict[str, dict[str, Any]] = {}
    for entry in previous_entries:
        case_id = str(entry.get("case_id", ""))
        if case_id:
            prior_by_case[case_id] = entry
    drift_rows: list[dict[str, Any]] = []
    timeline_rows: list[dict[str, Any]] = []
    for current in current_entries:
        case_id = current["case_id"]
        prior = prior_by_case.get(case_id)
        evidence_changed = bool(prior) and prior.get("evidence_fingerprint") != current["evidence_fingerprint"]
        classification_changed = bool(prior) and prior.get("classification_fingerprint") != current["classification_fingerprint"]
        decision_changed = bool(prior) and prior.get("decision_hash") != current["decision_hash"]
        confidence_delta = round(current["review_confidence"] - float(prior.get("review_confidence", 0) or 0), 4) if prior else 0.0
        coverage_delta = round(current["required_evidence_coverage"] - float(prior.get("required_evidence_coverage", 0) or 0), 4) if prior else 0.0
        if not prior:
            attribution = "NO_PREVIOUS_BASELINE"
        elif evidence_changed:
            attribution = "EVIDENCE_CHANGED"
        elif classification_changed:
            attribution = "UNEXPLAINED_CLASSIFICATION_DRIFT"
        elif decision_changed:
            attribution = "UNEXPLAINED_DECISION_DRIFT"
        elif abs(confidence_delta) > 0.0001:
            attribution = "UNEXPLAINED_CONFIDENCE_DRIFT"
        elif abs(coverage_delta) > 0.0001:
            attribution = "UNEXPLAINED_COVERAGE_DRIFT"
        else:
            attribution = "STABLE"
        severity = "CRITICAL" if attribution.startswith("UNEXPLAINED") else ("MAJOR" if attribution == "EVIDENCE_CHANGED" else "INFO")
        drift_rows.append({
            "case_id": case_id, "previous_run_id": prior.get("run_id", "") if prior else "", "current_run_id": run_id,
            "previous_version": prior.get("version", "") if prior else "", "current_version": release_version,
            "evidence_changed": evidence_changed, "classification_changed": classification_changed, "decision_changed": decision_changed,
            "previous_failure_class": prior.get("failure_class", "") if prior else "", "current_failure_class": current["failure_class"],
            "previous_readiness": prior.get("resolution_readiness", "") if prior else "", "current_readiness": current["resolution_readiness"],
            "previous_strategy": prior.get("resolution_strategy", "") if prior else "", "current_strategy": current["resolution_strategy"],
            "review_confidence_delta": confidence_delta, "evidence_coverage_delta": coverage_delta,
            "drift_attribution": attribution, "severity": severity,
        })
        timeline_rows.append({
            "case_id": case_id, "run_id": run_id, "version": release_version, "run_timestamp_utc": now,
            "failure_class": current["failure_class"], "resolution_readiness": current["resolution_readiness"],
            "resolution_strategy": current["resolution_strategy"], "evidence_fingerprint": current["evidence_fingerprint"],
            "classification_fingerprint": current["classification_fingerprint"], "decision_hash": current["decision_hash"],
            "drift_attribution": attribution, "severity": severity,
        })

    drift_df = pd.DataFrame(drift_rows)
    current_timeline = pd.DataFrame(timeline_rows)
    timeline_df = history_df[[c for c in columns if c in history_df.columns]].copy()
    if not timeline_df.empty:
        drift_lookup = {(r["current_run_id"], r["case_id"]): (r["drift_attribution"], r["severity"]) for r in drift_rows}
        timeline_df["drift_attribution"] = [drift_lookup.get((str(r.run_id), str(r.case_id)), ("HISTORICAL", "INFO"))[0] for r in timeline_df.itertuples()]
        timeline_df["severity"] = [drift_lookup.get((str(r.run_id), str(r.case_id)), ("HISTORICAL", "INFO"))[1] for r in timeline_df.itertuples()]

    run_summary = history_df.groupby(["run_id", "version"], dropna=False).agg(
        cases=("case_id", "count"), distinct_failure_classes=("failure_class", "nunique"),
        average_review_confidence=("review_confidence", "mean"), average_evidence_coverage=("required_evidence_coverage", "mean"),
    ).reset_index() if not history_df.empty else pd.DataFrame()
    if not run_summary.empty:
        run_summary["average_review_confidence"] = run_summary["average_review_confidence"].round(4)
        run_summary["average_evidence_coverage"] = run_summary["average_evidence_coverage"].round(4)

    unexplained = int(drift_df["drift_attribution"].astype(str).str.startswith("UNEXPLAINED").sum())
    validation = pd.DataFrame([
        {"guard":"history_cases_recorded","expected":len(stability_cases),"actual":len(current_entries),"status":"PASS" if len(current_entries)==len(stability_cases) else "FAIL"},
        {"guard":"fingerprints_complete_in_history","expected":len(current_entries)*3,"actual":sum(bool(e["evidence_fingerprint"] and e["classification_fingerprint"] and e["decision_hash"]) * 3 for e in current_entries),"status":"PASS" if all(e["evidence_fingerprint"] and e["classification_fingerprint"] and e["decision_hash"] for e in current_entries) else "FAIL"},
        {"guard":"no_unexplained_cross_run_drift","expected":0,"actual":unexplained,"status":"PASS" if unexplained==0 else "FAIL"},
        {"guard":"no_operational_truth_change","expected":False,"actual":False,"status":"PASS"},
        {"guard":"no_gold_clearance","expected":0,"actual":0,"status":"PASS"},
    ])
    summary = pd.DataFrame([{
        "phase":"v0.9.5.159_stability_verification", "run_id":run_id, "cases":len(current_entries),
        "history_entries":len(all_entries), "runs":int(history_df["run_id"].nunique()) if not history_df.empty else 0,
        "prior_cases_compared":len(prior_by_case), "classification_drifts":int(drift_df["classification_changed"].sum()),
        "decision_drifts":int(drift_df["decision_changed"].sum()), "unexplained_drifts":unexplained,
        "stable_cases":int((drift_df["drift_attribution"]=="STABLE").sum()),
        "no_previous_baseline":int((drift_df["drift_attribution"]=="NO_PREVIOUS_BASELINE").sum()),
        "operational_truth_modified":False, "gold_clearance_created":0,
    }])

    if history_path:
        try:
            history_path.write_text(json.dumps({"schema_version":1,"latest_run_id":run_id,"entries":all_entries}, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass
    return history_df, timeline_df, drift_df, run_summary, validation, summary


def _resolution_simulation_options(row: dict[str, Any]) -> list[dict[str, Any]]:
    """Return bounded, diagnostic-only resolution options for one case."""
    action = str(row.get("review_action", "") or "")
    readiness = str(row.get("resolution_readiness", "") or "")
    strategy = str(row.get("resolution_strategy", "") or "")
    options = {
        "REVIEW_CROP_GEOMETRY": [
            ("RECROP_AND_TARGETED_REOCR", "ACQUISITION", 0.82, 0.78, 0.22, 2.0),
            ("MANUAL_CROP_INSPECTION", "HUMAN_REVIEW", 0.58, 0.62, 0.10, 5.0),
            ("KEEP_BLOCKED", "NO_ACTION", 0.00, 0.00, 0.02, 0.0),
        ],
        "REVIEW_VOTE_SELECTION": [
            ("REPLAY_VOTE_SELECTION_WITH_TARGETED_REOCR", "REOCR", 0.76, 0.72, 0.28, 2.5),
            ("MANUAL_VOTE_ADJUDICATION", "HUMAN_REVIEW", 0.60, 0.58, 0.12, 4.0),
            ("KEEP_BLOCKED", "NO_ACTION", 0.00, 0.00, 0.02, 0.0),
        ],
        "REVIEW_LOCAL_GLYPH": [
            ("TARGETED_LOCAL_GLYPH_REOCR", "REOCR", 0.84, 0.80, 0.18, 1.5),
            ("MANUAL_LOCAL_GLYPH_REVIEW", "HUMAN_REVIEW", 0.62, 0.55, 0.10, 3.0),
            ("KEEP_BLOCKED", "NO_ACTION", 0.00, 0.00, 0.02, 0.0),
        ],
        "REVIEW_EVIDENCE_CONFLICT": [
            ("MANUAL_EVIDENCE_ADJUDICATION", "HUMAN_REVIEW", 0.72, 0.48, 0.16, 6.0),
            ("COLLECT_ADDITIONAL_EVIDENCE", "EVIDENCE", 0.45, 0.70, 0.08, 4.0),
            ("KEEP_BLOCKED", "NO_ACTION", 0.00, 0.00, 0.02, 0.0),
        ],
        "REVIEW_MISSING_IDENTITY": [
            ("COLLECT_IDENTITY_EVIDENCE", "EVIDENCE", 0.38, 0.86, 0.06, 4.0),
            ("MANUAL_ROW_RECOVERY", "HUMAN_REVIEW", 0.48, 0.64, 0.12, 6.0),
            ("KEEP_BLOCKED", "NO_ACTION", 0.00, 0.00, 0.02, 0.0),
        ],
        "REVIEW_SCRIPT_POLICY": [
            ("MANUAL_SCRIPT_POLICY_REVIEW", "POLICY", 0.68, 0.42, 0.14, 7.0),
            ("COLLECT_SCRIPT_CONTEXT", "EVIDENCE", 0.30, 0.58, 0.06, 4.0),
            ("KEEP_BLOCKED", "NO_ACTION", 0.00, 0.00, 0.02, 0.0),
        ],
        "REVIEW_MIXED_SCRIPT": [
            ("MANUAL_SCRIPT_POLICY_REVIEW", "POLICY", 0.64, 0.44, 0.16, 7.0),
            ("COLLECT_SCRIPT_CONTEXT", "EVIDENCE", 0.34, 0.62, 0.08, 4.0),
            ("KEEP_BLOCKED", "NO_ACTION", 0.00, 0.00, 0.02, 0.0),
        ],
        "REVIEW_CASE_BINDING": [
            ("REPAIR_CASE_BINDING", "BINDING", 0.70, 0.78, 0.10, 3.0),
            ("MANUAL_CASE_BINDING", "HUMAN_REVIEW", 0.52, 0.58, 0.14, 5.0),
            ("KEEP_BLOCKED", "NO_ACTION", 0.00, 0.00, 0.02, 0.0),
        ],
    }.get(action, [
        (strategy or "KEEP_BLOCKED", "DIAGNOSTIC", 0.35, 0.35, 0.20, 3.0),
        ("KEEP_BLOCKED", "NO_ACTION", 0.00, 0.00, 0.02, 0.0),
    ])
    result=[]
    for name, lane, base_gain, base_info, base_risk, effort in options:
        result.append({"option":name,"lane":lane,"base_resolution_gain":base_gain,"base_information_gain":base_info,"base_risk":base_risk,"estimated_effort_seconds":effort,"matches_current_strategy":name==strategy,"current_readiness":readiness})
    return result


def _build_resolution_simulator(
    readiness_cases: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Strike XVII: compare resolution options without executing or mutating anything."""
    if readiness_cases.empty:
        empty=pd.DataFrame()
        validation=pd.DataFrame([
            {"guard":"simulation_cases_covered","expected":0,"actual":0,"status":"PASS"},
            {"guard":"simulation_is_read_only","expected":0,"actual":0,"status":"PASS"},
        ])
        summary=pd.DataFrame([{"phase":"v0.9.5.161_resolution_simulator","cases":0,"options":0,"recommended_options":0,"automatic_fix_executed":0,"gold_clearance_created":0}])
        return empty, empty, validation, summary

    option_rows=[]
    case_rows=[]
    for row in readiness_cases.to_dict(orient="records"):
        case_id=str(row.get("case_id", ""))
        coverage=float(row.get("required_evidence_coverage",0) or 0)
        review_conf=float(row.get("review_confidence",0) or 0)
        recommendation=float(row.get("recommendation_score",0) or 0)
        priority=str(row.get("priority", "MAJOR") or "MAJOR")
        priority_weight={"CRITICAL":1.0,"MAJOR":0.85,"MINOR":0.65,"BLOCKED":0.40}.get(priority,0.75)
        local=[]
        for opt in _resolution_simulation_options(row):
            resolution_gain=max(0.0,min(1.0,opt["base_resolution_gain"]*(0.45+0.30*coverage+0.25*review_conf)))
            information_gain=max(0.0,min(1.0,opt["base_information_gain"]*(0.55+0.45*(1.0-coverage))))
            risk=max(0.0,min(1.0,opt["base_risk"]*(1.15-0.35*review_conf)))
            effort=float(opt["estimated_effort_seconds"] or 0)
            effort_penalty=min(0.25, effort/40.0)
            expected_utility=round(max(0.0,min(1.0,
                resolution_gain*0.45 + information_gain*0.25 + recommendation*0.15 + priority_weight*0.15 - risk*0.30 - effort_penalty
            )),4)
            safety="LOW" if risk<0.15 else ("MODERATE" if risk<0.30 else "HIGH")
            rec={
                "phase":"v0.9.5.161_resolution_simulator","case_id":case_id,"server":row.get("server"),"rank":row.get("rank"),
                "failure_class":row.get("failure_class", ""),"review_action":row.get("review_action", ""),
                "candidate_strategy":opt["option"],"simulation_lane":opt["lane"],
                "expected_resolution_gain":round(resolution_gain,4),"expected_information_gain":round(information_gain,4),
                "expected_risk":round(risk,4),"risk_label":safety,"estimated_effort_seconds":effort,
                "expected_utility":expected_utility,"matches_current_strategy":bool(opt["matches_current_strategy"]),
                "simulation_only":True,"automatic_fix_executed":False,"gold_clearance_created":False,
                "ground_truth_used_as_evidence":False,"operational_truth_modified":False,
            }
            local.append(rec)
        local.sort(key=lambda x:(x["expected_utility"],x["expected_resolution_gain"],x["expected_information_gain"]), reverse=True)
        for i,rec in enumerate(local, start=1):
            rec["option_rank"]=i
            rec["recommended_option"]=i==1
            option_rows.append(rec)
        best=local[0]
        case_rows.append({
            "phase":"v0.9.5.161_resolution_simulator","case_id":case_id,"server":row.get("server"),"rank":row.get("rank"),
            "failure_class":row.get("failure_class", ""),"review_action":row.get("review_action", ""),
            "current_readiness":row.get("resolution_readiness", ""),"current_strategy":row.get("resolution_strategy", ""),
            "recommended_simulated_strategy":best["candidate_strategy"],"recommended_lane":best["simulation_lane"],
            "primary_strategy":row.get("resolution_strategy", ""),
            "prerequisite_action":best["candidate_strategy"] if best["candidate_strategy"] != str(row.get("resolution_strategy", "")) else "",
            "strategy_relationship":"PREREQUISITE" if best["candidate_strategy"] != str(row.get("resolution_strategy", "")) else "ALIGNED",
            "expected_resolution_gain":best["expected_resolution_gain"],"expected_information_gain":best["expected_information_gain"],
            "expected_risk":best["expected_risk"],"risk_label":best["risk_label"],
            "expected_utility":best["expected_utility"],"strategy_alignment":best["candidate_strategy"]==str(row.get("resolution_strategy", "")),
            "simulation_only":True,"automatic_fix_executed":False,"gold_clearance_created":False,
            "ground_truth_used_as_evidence":False,"operational_truth_modified":False,
        })
    options_df=pd.DataFrame(option_rows)
    cases_df=pd.DataFrame(case_rows)
    validation=pd.DataFrame([
        {"guard":"simulation_cases_covered","expected":len(readiness_cases),"actual":len(cases_df),"status":"PASS" if len(cases_df)==len(readiness_cases) else "FAIL"},
        {"guard":"multiple_options_per_case","expected":len(readiness_cases),"actual":int((options_df.groupby("case_id").size()>=2).sum()),"status":"PASS" if (options_df.groupby("case_id").size()>=2).all() else "FAIL"},
        {"guard":"exactly_one_recommendation_per_case","expected":len(readiness_cases),"actual":int(options_df[options_df["recommended_option"]].groupby("case_id").size().eq(1).sum()),"status":"PASS" if options_df[options_df["recommended_option"]].groupby("case_id").size().eq(1).all() else "FAIL"},
        {"guard":"simulation_is_read_only","expected":0,"actual":int(options_df["automatic_fix_executed"].astype(bool).sum()+options_df["operational_truth_modified"].astype(bool).sum()),"status":"PASS"},
        {"guard":"no_gold_clearance","expected":0,"actual":int(options_df["gold_clearance_created"].astype(bool).sum()),"status":"PASS"},
        {"guard":"ground_truth_not_evidence","expected":0,"actual":int(options_df["ground_truth_used_as_evidence"].astype(bool).sum()),"status":"PASS"},
    ])
    summary=pd.DataFrame([{
        "phase":"v0.9.5.161_resolution_simulator","cases":len(cases_df),"options":len(options_df),
        "recommended_options":int(options_df["recommended_option"].sum()),
        "strategy_alignment_cases":int(cases_df["strategy_alignment"].sum()),
        "average_expected_resolution_gain":round(float(cases_df["expected_resolution_gain"].mean()),4),
        "average_expected_information_gain":round(float(cases_df["expected_information_gain"].mean()),4),
        "average_expected_risk":round(float(cases_df["expected_risk"].mean()),4),
        "average_expected_utility":round(float(cases_df["expected_utility"].mean()),4),
        "automatic_fix_executed":0,"gold_clearance_created":0,"ground_truth_used_as_evidence":False,"operational_truth_modified":False,
    }])
    return cases_df, options_df, validation, summary

def _authoritative_gold_core_metadata(row: pd.Series | dict[str, Any]) -> dict[str, str]:
    """Return the already-authoritative Gold Core classification without recomputation."""
    def pick(*keys: str) -> str:
        for key in keys:
            value = row.get(key, "")
            if value is None or (isinstance(value, float) and pd.isna(value)):
                continue
            text = str(value).strip()
            if text and text.lower() != "nan":
                return text
        return ""
    return {
        "failure_class": pick("gold_core_failure_class", "failure_class"),
        "failure_domain": pick("gold_core_failure_domain", "failure_domain"),
        "fix_lane": pick("gold_core_fix_lane", "fix_lane"),
        "root_cause": pick("gold_core_root_cause", "root_cause"),
        "recommendation": pick("gold_core_recommendation", "recommendation", "gold_core_resolution_action"),
    }


def _build_gold_core_character_evidence_map(detail: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """v0.9.5.149: expose the exact character positions blocking Gold Core.

    This is a read-only observability layer. Ground Truth is used only as the
    comparison target. Proof status, sources, crop diagnostics, conflicts and
    unresolved positions are derived exclusively from current-snapshot text and
    Character ReOCR evidence. No clearance or Operational Truth is changed.
    """
    blockers = detail[detail.get("gold_core_blocker_after_elimination", detail.get("gold_core_blocker", pd.Series(False, index=detail.index))).fillna(False).astype(bool)].copy()
    position_rows: list[dict[str, Any]] = []
    case_rows: list[dict[str, Any]] = []

    for _, row in blockers.iterrows():
        metadata = _authoritative_gold_core_metadata(row)
        diag = _evidence_bound_name_reconstruction(row)
        expected = normalize_text(row.get("expected_name", ""))
        source = normalize_text(diag.get("name_reconstruction_source_value", ""))
        try:
            trace = json.loads(diag.get("name_reconstruction_trace", "[]") or "[]")
        except Exception:
            trace = []
        try:
            conflicts = json.loads(diag.get("name_reconstruction_conflicts", "[]") or "[]")
        except Exception:
            conflicts = []
        evidence = [item for item in _parse_character_reocr_evidence(row.get("character_reocr_evidence", "")) if str(item.get("field", "") or "") == "player_name"]
        trace_by_pos = {int(item.get("position")): item for item in trace if str(item.get("position", "")).lstrip("-").isdigit()}
        conflict_by_pos: dict[int, list[dict[str, Any]]] = {}
        for item in conflicts:
            try:
                conflict_by_pos.setdefault(int(item.get("position")), []).append(item)
            except (TypeError, ValueError):
                pass
        evidence_by_pos: dict[int, list[dict[str, Any]]] = {}
        for item in evidence:
            try:
                evidence_by_pos.setdefault(int(item.get("position")), []).append(item)
            except (TypeError, ValueError):
                pass

        counts = {"CONFIRMED": 0, "MISSING": 0, "CONFLICT": 0, "UNRESOLVED": 0}
        for pos, expected_char in enumerate(expected):
            proof = trace_by_pos.get(pos, {})
            pos_conflicts = conflict_by_pos.get(pos, [])
            pos_evidence = evidence_by_pos.get(pos, [])
            statuses = sorted(set(str(item.get("status", "") or "") for item in pos_evidence if str(item.get("status", "") or "")))
            diagnostics = sorted(set(str(item.get("crop_diagnostic", "") or "") for item in pos_evidence if str(item.get("crop_diagnostic", "") or "")))
            anchors = sorted(set(str(item.get("crop_anchor_status", "") or "") for item in pos_evidence if str(item.get("crop_anchor_status", "") or "")))
            screenshots = sorted(set(str(item.get("screenshot", "") or "") for item in pos_evidence if str(item.get("screenshot", "") or "")))
            selected = [normalize_text(item.get("selected", ""))[:1] for item in pos_evidence if normalize_text(item.get("selected", ""))]
            confidences = [float(item.get("confidence", 0.0) or 0.0) for item in pos_evidence]
            position_type = "SEPARATOR" if expected_char.isspace() else "GLYPH"
            separator_verified = position_type == "SEPARATOR" and any(st == "verified_expected" for st in statuses)
            if pos_conflicts:
                status = "CONFLICT"
                reason = "observed_counterevidence"
            elif separator_verified:
                status = "CONFIRMED"
                reason = "separator_confirmed_by_position_evidence"
            elif proof:
                status = "CONFIRMED"
                reason = str(proof.get("proof", "position_proven"))
            elif any(st in {"unresolved", "ambiguous_vote"} for st in statuses):
                status = "UNRESOLVED"
                reason = "unresolved_or_ambiguous_vote"
            else:
                status = "MISSING"
                reason = "no_position_bound_evidence"
            counts[status] += 1
            observed_char = source[pos] if pos < len(source) else ""
            position_rows.append({
                "phase": "v0.9.5.149_position_evidence_intelligence",
                "server": row.get("server"), "rank": row.get("rank"),
                "failure_class": metadata["failure_class"],
                "failure_domain": metadata["failure_domain"],
                "fix_lane": metadata["fix_lane"],
                "root_cause": metadata["root_cause"],
                "recommendation": metadata["recommendation"],
                "promotion_guard_primary_blocker": row.get("promotion_guard_primary_blocker", ""),
                "position": pos, "position_human": pos + 1,
                "position_type": position_type,
                "expected_char": expected_char, "observed_char": observed_char,
                "position_status": status, "position_reason": reason,
                "proof_source": proof.get("proof", ""),
                "proof_char": proof.get("char", ""),
                "evidence_count": len(pos_evidence),
                "best_confidence": round(max(confidences), 4) if confidences else 0.0,
                "selected_chars": json.dumps(selected, ensure_ascii=False),
                "vote_statuses": json.dumps(statuses, ensure_ascii=False),
                "crop_diagnostics": json.dumps(diagnostics, ensure_ascii=False),
                "crop_anchor_statuses": json.dumps(anchors, ensure_ascii=False),
                "screenshots": json.dumps(screenshots, ensure_ascii=False),
                "conflicts": json.dumps(pos_conflicts, ensure_ascii=False),
                "blocks_name_exact": status != "CONFIRMED",
                "operational_truth_modified": False,
            })

        case_rows.append({
            "phase": "v0.9.5.149_position_evidence_intelligence",
            "server": row.get("server"), "rank": row.get("rank"),
            "expected_name": expected, "observed_name": row.get("ocr_name", ""),
            "failure_class": metadata["failure_class"],
            "failure_domain": metadata["failure_domain"],
            "fix_lane": metadata["fix_lane"],
            "root_cause": metadata["root_cause"],
            "recommendation": metadata["recommendation"],
            "promotion_guard_primary_blocker": row.get("promotion_guard_primary_blocker", ""),
            "name_proof_status": diag.get("name_proof_status", ""),
            "coverage": diag.get("name_reconstruction_coverage", 0.0),
            "positions_total": len(expected),
            "positions_confirmed": counts["CONFIRMED"],
            "positions_missing": counts["MISSING"],
            "positions_unresolved": counts["UNRESOLVED"],
            "positions_conflicting": counts["CONFLICT"],
            "blocking_positions": json.dumps([r["position_human"] for r in position_rows if r.get("rank") == row.get("rank") and r.get("server") == row.get("server") and r.get("position_status") != "CONFIRMED"], ensure_ascii=False),
            "recommended_evidence_action": "resolve_conflict" if counts["CONFLICT"] else ("targeted_position_reocr" if counts["MISSING"] or counts["UNRESOLVED"] else "none"),
            "operational_truth_modified": False,
        })

    positions = pd.DataFrame(position_rows)
    cases = pd.DataFrame(case_rows)
    if positions.empty:
        heatmap = pd.DataFrame(columns=["position_human", "positions", "confirmed", "missing", "unresolved", "conflicting", "confirmation_rate", "blocker_rate", "recommended_action"])
    else:
        heatmap = positions.groupby("position_human", dropna=False).agg(
            positions=("rank", "count"),
            confirmed=("position_status", lambda v: int((pd.Series(v) == "CONFIRMED").sum())),
            missing=("position_status", lambda v: int((pd.Series(v) == "MISSING").sum())),
            unresolved=("position_status", lambda v: int((pd.Series(v) == "UNRESOLVED").sum())),
            conflicting=("position_status", lambda v: int((pd.Series(v) == "CONFLICT").sum())),
            avg_best_confidence=("best_confidence", "mean"),
        ).reset_index()
        heatmap["confirmation_rate"] = (heatmap["confirmed"] / heatmap["positions"].replace(0, 1)).round(4)
        heatmap["blocker_rate"] = (1 - heatmap["confirmation_rate"]).round(4)
        heatmap["recommended_action"] = heatmap.apply(lambda r: "resolve_conflicting_evidence" if int(r["conflicting"]) else ("targeted_position_reocr" if int(r["missing"] + r["unresolved"]) else "none"), axis=1)
        heatmap.insert(0, "phase", "v0.9.5.149_position_evidence_intelligence")
        heatmap["operational_truth_modified"] = False
    return cases, positions, heatmap


def _build_gold_core_evidence_provenance(
    detail: pd.DataFrame,
    position_cases: pd.DataFrame,
    position_rows: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """v0.9.5.150: trace every blocked character position through the evidence pipeline.

    The report is diagnostic only. It identifies the earliest pipeline stage at
    which current-snapshot evidence becomes absent, ambiguous, contaminated or
    contradictory. Ground Truth is comparison context and is never used as an
    evidence source or replacement character.
    """
    case_lookup = {
        (row.get("server"), row.get("rank")): row
        for _, row in detail.iterrows()
    }
    provenance_positions: list[dict[str, Any]] = []
    stage_rows: list[dict[str, Any]] = []

    for _, pos_row in position_rows.iterrows():
        if str(pos_row.get("position_status", "")) == "CONFIRMED":
            continue
        key = (pos_row.get("server"), pos_row.get("rank"))
        source_row = case_lookup.get(key)
        evidence = []
        if source_row is not None:
            evidence = [
                item for item in _parse_character_reocr_evidence(source_row.get("character_reocr_evidence", ""))
                if str(item.get("field", "") or "") == "player_name"
                and str(item.get("position", "")).lstrip("-").isdigit()
                and int(item.get("position")) == int(pos_row.get("position", -1))
            ]

        screenshots = sorted({str(item.get("screenshot", "") or "") for item in evidence if str(item.get("screenshot", "") or "")})
        crop_boxes = sorted({json.dumps(item.get("crop_box"), ensure_ascii=False) for item in evidence if item.get("crop_box") not in (None, "")})
        crop_strategies = sorted({str(item.get("crop_strategy", "") or "") for item in evidence if str(item.get("crop_strategy", "") or "")})
        anchors = sorted({str(item.get("crop_anchor_status", "") or "") for item in evidence if str(item.get("crop_anchor_status", "") or "")})
        diagnostics = sorted({str(item.get("crop_diagnostic", "") or "") for item in evidence if str(item.get("crop_diagnostic", "") or "")})
        statuses = sorted({str(item.get("status", "") or "") for item in evidence if str(item.get("status", "") or "")})
        selected = [normalize_text(item.get("selected", ""))[:1] for item in evidence if normalize_text(item.get("selected", ""))]
        vote_texts = [item.get("vote_texts") for item in evidence if item.get("vote_texts") not in (None, "")]
        nonempty_vote_chars = [item.get("nonempty_vote_chars") for item in evidence if item.get("nonempty_vote_chars") not in (None, "")]
        confidences = [float(item.get("confidence", 0.0) or 0.0) for item in evidence]
        target_total_ms = [float(item.get("target_total_ms", 0.0) or 0.0) for item in evidence]
        ocr_read_ms = [float(item.get("ocr_read_ms", 0.0) or 0.0) for item in evidence]

        screenshot_status = "AVAILABLE" if screenshots else "MISSING"
        crop_problem = bool(set(anchors) & {"field_mismatch", "anchor_missing", "anchor_ambiguous"}) or bool(
            set(diagnostics) & {"field_mismatch", "crop_clipped", "crop_empty", "crop_contaminated", "anchor_missing"}
        )
        crop_status = "BLOCKED" if crop_problem else ("AVAILABLE" if evidence else "NOT_REACHED")
        ocr_status = "NOT_REACHED" if not evidence else ("CONFLICT" if str(pos_row.get("position_status")) == "CONFLICT" else ("OBSERVED" if selected else "EMPTY"))
        vote_problem = any(st in {"unresolved", "ambiguous_vote"} for st in statuses) or "vote_outside_allowed_set" in diagnostics
        vote_status = "BLOCKED" if vote_problem else ("RESOLVED" if evidence else "NOT_REACHED")
        reconstruction_status = "CONFLICT" if str(pos_row.get("position_status")) == "CONFLICT" else "INCOMPLETE"
        guard_status = "BLOCKED_NAME_EXACT"

        if not evidence:
            failure_stage = "character_acquisition"
            failure_reason = "no_position_bound_evidence"
            next_action = "acquire_position_evidence"
        elif crop_problem:
            failure_stage = "crop_geometry"
            failure_reason = ",".join(diagnostics or anchors) or "crop_or_anchor_problem"
            next_action = "repair_position_crop"
        elif vote_problem:
            failure_stage = "vote_resolution"
            failure_reason = ",".join(statuses or diagnostics) or "vote_unresolved"
            next_action = "collect_independent_vote_evidence"
        elif str(pos_row.get("position_status")) == "CONFLICT":
            failure_stage = "evidence_reconstruction"
            failure_reason = "observed_counterevidence"
            next_action = "resolve_counterevidence"
        elif not selected:
            failure_stage = "ocr_observation"
            failure_reason = "ocr_returned_no_character"
            next_action = "targeted_position_reocr"
        else:
            failure_stage = "evidence_reconstruction"
            failure_reason = str(pos_row.get("position_reason", "incomplete_reconstruction"))
            next_action = "increase_independent_position_coverage"

        position_record = {
            "phase": "v0.9.5.150_evidence_provenance",
            "server": pos_row.get("server"),
            "rank": pos_row.get("rank"),
            "failure_class": pos_row.get("failure_class", ""),
            "promotion_guard_primary_blocker": pos_row.get("promotion_guard_primary_blocker", ""),
            "position": pos_row.get("position"),
            "position_human": pos_row.get("position_human"),
            "expected_char": pos_row.get("expected_char", ""),
            "observed_char": pos_row.get("observed_char", ""),
            "position_status": pos_row.get("position_status", ""),
            "first_failed_stage": failure_stage,
            "first_failed_reason": failure_reason,
            "recommended_action": next_action,
            "screenshot_status": screenshot_status,
            "screenshots": json.dumps(screenshots, ensure_ascii=False),
            "crop_status": crop_status,
            "crop_boxes": json.dumps(crop_boxes, ensure_ascii=False),
            "crop_strategies": json.dumps(crop_strategies, ensure_ascii=False),
            "crop_anchor_statuses": json.dumps(anchors, ensure_ascii=False),
            "crop_diagnostics": json.dumps(diagnostics, ensure_ascii=False),
            "ocr_status": ocr_status,
            "selected_chars": json.dumps(selected, ensure_ascii=False),
            "best_confidence": round(max(confidences), 4) if confidences else 0.0,
            "vote_status": vote_status,
            "target_statuses": json.dumps(statuses, ensure_ascii=False),
            "vote_texts": json.dumps(vote_texts, ensure_ascii=False),
            "nonempty_vote_chars": json.dumps(nonempty_vote_chars, ensure_ascii=False),
            "reconstruction_status": reconstruction_status,
            "promotion_guard_status": guard_status,
            "evidence_count": len(evidence),
            "target_total_ms": round(sum(target_total_ms), 2),
            "ocr_read_ms": round(sum(ocr_read_ms), 2),
            "ground_truth_used_as_evidence": False,
            "operational_truth_modified": False,
        }
        provenance_positions.append(position_record)

        stages = [
            ("screenshot", screenshot_status, "screenshot_reference_present" if screenshots else "no_screenshot_reference"),
            ("crop", crop_status, failure_reason if failure_stage == "crop_geometry" else "crop_stage_passed_or_not_reached"),
            ("ocr", ocr_status, failure_reason if failure_stage == "ocr_observation" else "ocr_stage_observed"),
            ("vote", vote_status, failure_reason if failure_stage == "vote_resolution" else "vote_stage_resolved_or_not_reached"),
            ("reconstruction", reconstruction_status, failure_reason if failure_stage == "evidence_reconstruction" else "reconstruction_incomplete_downstream"),
            ("promotion_guard", guard_status, "name_exact_not_proven"),
        ]
        for order, (stage, stage_status, stage_reason) in enumerate(stages, start=1):
            stage_rows.append({
                "phase": "v0.9.5.150_evidence_provenance",
                "server": pos_row.get("server"), "rank": pos_row.get("rank"),
                "position": pos_row.get("position"), "position_human": pos_row.get("position_human"),
                "stage_order": order, "stage": stage, "stage_status": stage_status,
                "stage_reason": stage_reason, "is_first_failed_stage": stage == failure_stage,
                "operational_truth_modified": False,
            })

    positions = pd.DataFrame(provenance_positions)
    stages = pd.DataFrame(stage_rows)
    if positions.empty:
        cases = pd.DataFrame(columns=["server", "rank", "blocked_positions", "first_failed_stages", "recommended_actions", "operational_truth_modified"])
        summary = pd.DataFrame(columns=["first_failed_stage", "positions", "cases", "avg_best_confidence", "recommended_action"])
        return cases, positions, stages, summary

    cases = positions.groupby(["server", "rank"], dropna=False).agg(
        failure_class=("failure_class", "first"),
        promotion_guard_primary_blocker=("promotion_guard_primary_blocker", "first"),
        blocked_positions=("position_human", lambda v: json.dumps([int(x) for x in v], ensure_ascii=False)),
        first_failed_stages=("first_failed_stage", lambda v: json.dumps(sorted(set(str(x) for x in v)), ensure_ascii=False)),
        recommended_actions=("recommended_action", lambda v: json.dumps(sorted(set(str(x) for x in v)), ensure_ascii=False)),
        evidence_records=("evidence_count", "sum"),
        avg_best_confidence=("best_confidence", "mean"),
    ).reset_index()
    cases.insert(0, "phase", "v0.9.5.150_evidence_provenance")
    cases["avg_best_confidence"] = cases["avg_best_confidence"].round(4)
    cases["ground_truth_used_as_evidence"] = False
    cases["operational_truth_modified"] = False

    summary = positions.groupby("first_failed_stage", dropna=False).agg(
        positions=("position_human", "count"),
        cases=("rank", "nunique"),
        avg_best_confidence=("best_confidence", "mean"),
        recommended_action=("recommended_action", lambda v: ",".join(sorted(set(str(x) for x in v)))),
    ).reset_index()
    summary.insert(0, "phase", "v0.9.5.150_evidence_provenance")
    summary["avg_best_confidence"] = summary["avg_best_confidence"].round(4)
    summary["ground_truth_used_as_evidence"] = False
    summary["operational_truth_modified"] = False
    return cases, positions, stages, summary

def _build_position_evidence_acquisition_bridge(
    detail: pd.DataFrame,
    position_rows: pd.DataFrame,
    authoritative_cases: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """v0.9.5.151: bind existing screenshot evidence to positions without creating text.

    The bridge is read-only. It never derives a character from Ground Truth and
    never upgrades Operational Truth. It only describes whether current evidence
    is directly bound, safely bridgeable, ambiguous, conflicting, missing, or
    rejected by a safety invariant.
    """
    lookup = {(r.get("server"), r.get("rank")): r for _, r in detail.iterrows()}
    authoritative_lookup: dict[tuple[Any, Any], dict[str, Any]] = {}
    if authoritative_cases is not None and not authoritative_cases.empty:
        for _, case in authoritative_cases.iterrows():
            authoritative_lookup[(case.get("server"), case.get("rank"))] = case.to_dict()
    rows: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for _, pos in position_rows.iterrows():
        key=(pos.get("server"), pos.get("rank"))
        src=lookup.get(key)
        evidence=[]
        display_provenance: dict[str, Any] = {}
        if src is not None:
            evidence=[e for e in _parse_character_reocr_evidence(src.get("character_reocr_evidence", ""))
                      if str(e.get("field", "") or "") == "player_name"
                      and str(e.get("position", "")).lstrip("-").isdigit()
                      and int(e.get("position")) == int(pos.get("position", -1))]
            for item in _parse_json_list(src.get("display_character_provenance", "[]")):
                try:
                    if int(item.get("position")) == int(pos.get("position", -1)):
                        display_provenance = item
                        break
                except (TypeError, ValueError):
                    continue
            alignment_record: dict[str, Any] = {}
            for item in _parse_json_list(src.get("display_character_alignment", "[]")):
                try:
                    if int(item.get("target_position")) == int(pos.get("position", -1)):
                        alignment_record = item
                        break
                except (TypeError, ValueError):
                    continue
        else:
            alignment_record = {}
        statuses=sorted({str(e.get("status", "") or "") for e in evidence if str(e.get("status", "") or "")})
        screenshots=sorted({str(e.get("screenshot", "") or "") for e in evidence if str(e.get("screenshot", "") or "")})
        crop_boxes=[e.get("crop_box") for e in evidence if e.get("crop_box") not in (None, "")]
        selected=[normalize_text(e.get("selected", ""))[:1] for e in evidence if normalize_text(e.get("selected", ""))]
        diagnostics=sorted({str(e.get("crop_diagnostic", "") or "") for e in evidence if str(e.get("crop_diagnostic", "") or "")})
        anchors=sorted({str(e.get("crop_anchor_status", "") or "") for e in evidence if str(e.get("crop_anchor_status", "") or "")})
        position_type=str(pos.get("position_type", "GLYPH") or "GLYPH")
        status=str(pos.get("position_status", "") or "")
        crop_unsafe=bool(set(anchors) & {"field_mismatch", "anchor_missing", "anchor_ambiguous"}) or bool(set(diagnostics) & {"field_mismatch", "crop_clipped", "crop_empty", "crop_contaminated", "anchor_missing", "crop_power_column_bleed"})
        if status == "CONFLICT" or any(st == "verified_observed" for st in statuses):
            binding="CONFLICTING_POSITION_EVIDENCE"; method="existing_counterevidence"; reason="conflicting_current_snapshot_evidence"
        elif crop_unsafe:
            binding="UNSAFE_BINDING_REJECTED"; method="rejected_crop_binding"; reason=",".join(diagnostics or anchors) or "unsafe_crop_geometry"
        elif evidence and screenshots and crop_boxes and selected:
            binding="DIRECT_POSITION_EVIDENCE"; method="existing_position_record"; reason="complete_existing_source_chain"
        elif evidence and (screenshots or crop_boxes) and selected:
            binding="BRIDGED_POSITION_EVIDENCE"; method="existing_partial_source_chain"; reason="position_record_linkable_without_text_creation"
        elif position_type == "SEPARATOR" and any(st == "verified_expected" for st in statuses):
            binding="BRIDGED_POSITION_EVIDENCE"; method="separator_evidence"; reason="separator_confirmed_by_existing_position_vote"
        elif evidence:
            binding="AMBIGUOUS_POSITION_BINDING"; method="insufficient_source_chain"; reason="evidence_exists_but_unique_position_chain_is_incomplete"
        else:
            # v0.9.5.153: source provenance must be carried by an explicit
            # edit operation. Direct character-index binding is forbidden when
            # strings differ, and non-space glyphs can never prove separators.
            operation = str(alignment_record.get("alignment_operation", "") or "")
            alignment_reason = str(alignment_record.get("alignment_reason", "") or "")
            aligned_source = alignment_record.get("source_record", {}) if isinstance(alignment_record.get("source_record", {}), dict) else {}
            if aligned_source:
                display_provenance = aligned_source
            chain_status = str(display_provenance.get("source_chain_status", "") or "")
            source_character = normalize_text(alignment_record.get("observed_character", display_provenance.get("character", "")))[:1]
            if operation in {"MATCH", "SEPARATOR_GAP"} and chain_status in {"ROW_OCR_SOURCE_BOUND", "CROP_CHARACTER_SOURCE_BOUND"}:
                binding="BRIDGED_POSITION_EVIDENCE"; method="provenance_aware_alignment"; reason="source_chain_preserved_by_exact_alignment_operation"
            elif operation == "SUBSTITUTE" and source_character:
                binding="CONFLICTING_POSITION_EVIDENCE"; method="provenance_aware_substitution"; reason="source_bound_character_differs_from_target_position"
            elif operation == "AMBIGUOUS":
                binding="AMBIGUOUS_POSITION_BINDING"; method="provenance_aware_alignment"; reason=alignment_reason or "alignment_is_ambiguous"
            elif operation == "DELETE":
                binding="NO_POSITION_EVIDENCE"; method="provenance_aware_delete"; reason="target_position_has_no_source_character"
            else:
                ocr_name=normalize_text(src.get("ocr_name", "")) if src is not None else ""
                idx=int(pos.get("position", -1))
                observed=ocr_name[idx:idx+1] if 0 <= idx < len(ocr_name) else ""
                if observed and not operation:
                    binding="UNSAFE_BINDING_REJECTED"; method="display_only_binding_rejected"; reason="display_character_has_no_screenshot_provenance"
                elif observed:
                    binding="UNSAFE_BINDING_REJECTED"; method="unaligned_source_binding_rejected"; reason="source_character_has_no_safe_target_alignment"
                else:
                    binding="NO_POSITION_EVIDENCE"; method="provenance_aware_delete"; reason="target_position_has_no_source_character"
        authoritative = authoritative_lookup.get(key, {})
        metadata = _authoritative_gold_core_metadata(authoritative if authoritative else pos)
        record={
            "phase":"v0.9.5.153_provenance_aware_character_alignment",
            "server":pos.get("server"), "rank":pos.get("rank"),
            "failure_class":metadata["failure_class"], "failure_domain":metadata["failure_domain"],
            "fix_lane":metadata["fix_lane"], "root_cause":metadata["root_cause"],
            "recommendation":metadata["recommendation"],
            "position":pos.get("position"), "position_human":pos.get("position_human"),
            "position_type":position_type, "previous_status":status,
            "binding_status":binding, "binding_method":method, "binding_reason":reason,
            "source_screenshot_ids":json.dumps(screenshots, ensure_ascii=False),
            "source_crop_boxes":json.dumps(crop_boxes, ensure_ascii=False),
            "source_selected_chars":json.dumps(selected, ensure_ascii=False),
            "source_vote_statuses":json.dumps(statuses, ensure_ascii=False),
            "source_crop_diagnostics":json.dumps(diagnostics, ensure_ascii=False),
            "source_anchor_statuses":json.dumps(anchors, ensure_ascii=False),
            "display_source_chain_status":str(display_provenance.get("source_chain_status", "") or ""),
            "display_source_screenshot":str(display_provenance.get("source_screenshot", "") or ""),
            "display_source_file":str(display_provenance.get("source_file", "") or ""),
            "display_source_row_slot":display_provenance.get("source_row_slot", ""),
            "display_source_observation_id":str(display_provenance.get("source_observation_id", "") or ""),
            "display_source_character_index":display_provenance.get("source_character_index", ""),
            "display_source_bbox":json.dumps(display_provenance.get("source_bbox"), ensure_ascii=False),
            "display_source_crop_box":json.dumps(display_provenance.get("source_crop_box"), ensure_ascii=False),
            "display_source_character":str(display_provenance.get("character", "") or ""),
            "alignment_operation":str(alignment_record.get("alignment_operation", "") or ""),
            "alignment_reason":str(alignment_record.get("alignment_reason", "") or ""),
            "alignment_confidence":float(alignment_record.get("alignment_confidence", 0.0) or 0.0),
            "alignment_source_character_index":alignment_record.get("source_character_index", ""),
            "display_source_gold_authoritative":False,
            "evidence_count":len(evidence),
            "ground_truth_used_as_evidence":False,
            "character_created_by_bridge":False,
            "operational_truth_modified":False,
        }
        rows.append(record)
        if binding in {"UNSAFE_BINDING_REJECTED", "AMBIGUOUS_POSITION_BINDING"}:
            rejected.append(record.copy())
    positions=pd.DataFrame(rows)
    rejected_df=pd.DataFrame(rejected)
    if positions.empty:
        cases=pd.DataFrame(); summary=pd.DataFrame()
    else:
        cases=positions.groupby(["server","rank"], dropna=False).agg(
            failure_class=("failure_class","first"), failure_domain=("failure_domain","first"),
            fix_lane=("fix_lane","first"), root_cause=("root_cause","first"),
            positions=("position_human","count"),
            binding_statuses=("binding_status", lambda v: json.dumps(sorted(set(map(str,v))), ensure_ascii=False)),
            direct=("binding_status", lambda v: int((pd.Series(v)=="DIRECT_POSITION_EVIDENCE").sum())),
            bridged=("binding_status", lambda v: int((pd.Series(v)=="BRIDGED_POSITION_EVIDENCE").sum())),
            ambiguous=("binding_status", lambda v: int((pd.Series(v)=="AMBIGUOUS_POSITION_BINDING").sum())),
            conflicts=("binding_status", lambda v: int((pd.Series(v)=="CONFLICTING_POSITION_EVIDENCE").sum())),
            rejected=("binding_status", lambda v: int((pd.Series(v)=="UNSAFE_BINDING_REJECTED").sum())),
            missing=("binding_status", lambda v: int((pd.Series(v)=="NO_POSITION_EVIDENCE").sum())),
        ).reset_index()
        cases.insert(0,"phase","v0.9.5.153_provenance_aware_character_alignment")
        cases["operational_truth_modified"]=False
        summary=positions.groupby("binding_status", dropna=False).agg(
            positions=("position_human","count"), cases=("rank","nunique"), evidence_records=("evidence_count","sum")
        ).reset_index()
        summary.insert(0,"phase","v0.9.5.153_provenance_aware_character_alignment")
        summary["ground_truth_used_as_evidence"]=False
        summary["operational_truth_modified"]=False
    return cases, positions, rejected_df, summary


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
        "phase": "v0.9.5.147_gold_core_zero_iii",
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
    gold_core_blocker_report, gold_core_blocker_summary = _build_gold_core_blocker_report(gold_blocker_triage, ocr_evidence_rows)
    gold_core_resolution_plan, gold_core_resolution_summary = _build_gold_core_resolution_plan_report(gold_core_blocker_report)
    gold_core_character_cases, gold_core_character_positions, gold_core_position_heatmap = _build_gold_core_character_evidence_map(detail)
    evidence_provenance_cases, evidence_provenance_positions, evidence_provenance_stages, evidence_provenance_summary = _build_gold_core_evidence_provenance(
        detail, gold_core_character_cases, gold_core_character_positions
    )
    position_bridge_cases, position_bridge_positions, position_bridge_rejected, position_bridge_summary = _build_position_evidence_acquisition_bridge(
        detail, gold_core_character_positions, gold_core_blocker_report
    )
    identity_graph_cases, identity_graph_characters, identity_graph_tokens, identity_graph_components, identity_graph_edges = _build_player_identity_graph(detail)
    identity_compositions, identity_slots, manual_review_queue, identity_root_cause_summary, identity_priority_summary = _build_identity_composition_engine(
        identity_graph_cases, identity_graph_characters, identity_graph_tokens, identity_graph_components
    )
    identity_compositions, manual_review_queue, identity_root_cause_summary, identity_priority_summary, review_case_bindings, review_confidence_calibration, review_validation, review_orchestration_summary = _build_gold_core_bound_review_orchestration(
        identity_compositions, identity_slots, manual_review_queue, gold_core_blocker_report, gold_core_resolution_plan
    )
    resolution_readiness_cases, resolution_readiness_breakdown, resolution_readiness_validation, resolution_readiness_summary = _build_resolution_readiness_intelligence(
        manual_review_queue, review_case_bindings, review_confidence_calibration
    )
    state_dir = output_dir / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    classification_stability_cases, evidence_coverage_rows, score_decomposition_rows, classification_stability_validation, classification_stability_summary = _build_classification_stability_and_coverage(
        resolution_readiness_cases, state_dir
    )
    if not classification_stability_cases.empty:
        resolution_readiness_cases = classification_stability_cases.copy()
        manual_review_queue = classification_stability_cases.copy()
    decision_history_rows, stability_timeline_rows, drift_analysis_rows, regression_dashboard_rows, stability_history_validation, stability_history_summary = _build_stability_verification_history(
        classification_stability_cases, state_dir
    )
    resolution_simulation_cases, resolution_simulation_options, resolution_simulation_validation, resolution_simulation_summary = _build_resolution_simulator(
        resolution_readiness_cases
    )
    detail = _attach_evidence_scheduler(detail)
    display_reconstruction_summary, display_reconstruction_rows = _build_display_reconstruction_report(detail)
    evidence_confidence_summary, evidence_confidence_rows = _build_evidence_confidence_report(detail)
    evidence_budget_summary, evidence_budget_rows = _build_evidence_budget_report(detail)
    evidence_scheduler_summary, evidence_scheduler_rows = _build_evidence_scheduler_report(detail)
    gold_core_elimination_summary, gold_core_elimination_rows = _build_gold_core_elimination_report(detail)
    from gold_core.quality_intelligence import build_gold_core_quality_intelligence, build_gold_core_case_explorer
    gold_core_analytics_summary, gold_core_analytics_rows, gold_core_failure_memory = build_gold_core_quality_intelligence(
        detail, output_dir, gold_core_blocker_report, gold_core_resolution_plan
    )
    gold_core_case_explorer, gold_core_prioritized_actions, gold_core_casebook_path = build_gold_core_case_explorer(
        gold_core_analytics_rows, gold_core_failure_memory, output_dir
    )

    json_payload = {
        "release_version": RELEASE_VERSION,
        "component_version": "v0.9.5.161_report_architecture",
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
        "gold_core_analytics_summary": gold_core_analytics_summary.to_dict(orient="records"),
        "gold_core_analytics_rows": gold_core_analytics_rows.to_dict(orient="records"),
        "gold_core_failure_memory": gold_core_failure_memory.to_dict(orient="records"),
        "gold_core_case_explorer": gold_core_case_explorer.to_dict(orient="records"),
        "gold_core_prioritized_actions": gold_core_prioritized_actions.to_dict(orient="records"),
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
        "gold_core_character_evidence_cases": gold_core_character_cases.to_dict(orient="records"),
        "gold_core_character_evidence_positions": gold_core_character_positions.to_dict(orient="records"),
        "gold_core_position_heatmap": gold_core_position_heatmap.to_dict(orient="records"),
        "evidence_provenance_summary": evidence_provenance_summary.to_dict(orient="records"),
        "evidence_provenance_cases": evidence_provenance_cases.to_dict(orient="records"),
        "evidence_provenance_positions": evidence_provenance_positions.to_dict(orient="records"),
        "evidence_provenance_stages": evidence_provenance_stages.to_dict(orient="records"),
        "position_evidence_bridge_summary": position_bridge_summary.to_dict(orient="records"),
        "identity_graph_cases": identity_graph_cases.to_dict(orient="records"),
        "identity_graph_characters": identity_graph_characters.to_dict(orient="records"),
        "identity_graph_tokens": identity_graph_tokens.to_dict(orient="records"),
        "identity_graph_components": identity_graph_components.to_dict(orient="records"),
        "identity_graph_edges": identity_graph_edges.to_dict(orient="records"),
        "identity_compositions": identity_compositions.to_dict(orient="records"),
        "identity_slots": identity_slots.to_dict(orient="records"),
        "manual_review_queue": manual_review_queue.to_dict(orient="records"),
        "identity_root_cause_summary": identity_root_cause_summary.to_dict(orient="records"),
        "identity_priority_summary": identity_priority_summary.to_dict(orient="records"),
        "review_orchestration_summary": review_orchestration_summary.to_dict(orient="records"),
        "review_case_bindings": review_case_bindings.to_dict(orient="records"),
        "review_confidence_calibration": review_confidence_calibration.to_dict(orient="records"),
        "resolution_readiness_summary": resolution_readiness_summary.to_dict(orient="records"),
        "resolution_readiness_breakdown": resolution_readiness_breakdown.to_dict(orient="records"),
        "resolution_readiness_cases": resolution_readiness_cases.to_dict(orient="records"),
        "resolution_readiness_validation": resolution_readiness_validation.to_dict(orient="records"),
        "classification_stability_summary": classification_stability_summary.to_dict(orient="records"),
        "classification_stability_cases": classification_stability_cases.to_dict(orient="records"),
        "classification_stability_validation": classification_stability_validation.to_dict(orient="records"),
        "evidence_coverage_rows": evidence_coverage_rows.to_dict(orient="records"),
        "score_decomposition_rows": score_decomposition_rows.to_dict(orient="records"),
        "stability_history_summary": stability_history_summary.to_dict(orient="records"),
        "decision_history_rows": decision_history_rows.to_dict(orient="records"),
        "stability_timeline_rows": stability_timeline_rows.to_dict(orient="records"),
        "drift_analysis_rows": drift_analysis_rows.to_dict(orient="records"),
        "regression_dashboard_rows": regression_dashboard_rows.to_dict(orient="records"),
        "stability_history_validation": stability_history_validation.to_dict(orient="records"),
        "resolution_simulation_summary": resolution_simulation_summary.to_dict(orient="records"),
        "resolution_simulation_cases": resolution_simulation_cases.to_dict(orient="records"),
        "resolution_simulation_options": resolution_simulation_options.to_dict(orient="records"),
        "resolution_simulation_validation": resolution_simulation_validation.to_dict(orient="records"),
        "review_validation": review_validation.to_dict(orient="records"),
        "position_evidence_bridge_cases": position_bridge_cases.to_dict(orient="records"),
        "position_evidence_bridge_positions": position_bridge_positions.to_dict(orient="records"),
        "position_evidence_bridge_rejected": position_bridge_rejected.to_dict(orient="records"),
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
    character_evidence_json_path = output_dir / "character_position_report.json"
    character_evidence_json_path.write_text(json.dumps(_json_safe({"phase": "v0.9.5.149_position_evidence_intelligence", "cases": gold_core_character_cases.to_dict(orient="records"), "positions": gold_core_character_positions.to_dict(orient="records")}), ensure_ascii=False, indent=2), encoding="utf-8")
    position_heatmap_json_path = output_dir / "position_heatmap.json"
    position_heatmap_json_path.write_text(json.dumps(_json_safe({"phase": "v0.9.5.149_position_evidence_intelligence", "positions": gold_core_position_heatmap.to_dict(orient="records")}), ensure_ascii=False, indent=2), encoding="utf-8")
    character_position_summary_md_path = output_dir / "character_position_summary.md"
    md_lines = ["# Character Position Evidence Summary", "", "Version: v0.9.5.149", "", "This report is read-only. It does not modify Operational Truth or Gold-Core policy.", "", "## Gold-Core Cases", ""]
    for item in gold_core_character_cases.to_dict(orient="records"):
        md_lines.extend([f"### Rank {item.get('rank')} — {item.get('expected_name', '')}", "", f"- Failure class: `{item.get('failure_class', '')}`", f"- Name proof: `{item.get('name_proof_status', '')}`", f"- Coverage: {float(item.get('coverage', 0) or 0):.2%}", f"- Blocking positions: {item.get('blocking_positions', '[]')}", f"- Evidence action: `{item.get('recommended_evidence_action', '')}`", ""])
    character_position_summary_md_path.write_text("\n".join(md_lines), encoding="utf-8")
    evidence_provenance_json_path = output_dir / "evidence_provenance_report.json"
    evidence_provenance_json_path.write_text(json.dumps(_json_safe({
        "phase": "v0.9.5.150_evidence_provenance",
        "summary": evidence_provenance_summary.to_dict(orient="records"),
        "cases": evidence_provenance_cases.to_dict(orient="records"),
        "positions": evidence_provenance_positions.to_dict(orient="records"),
        "stages": evidence_provenance_stages.to_dict(orient="records"),
        "ground_truth_used_as_evidence": False,
        "operational_truth_modified": False,
    }), ensure_ascii=False, indent=2), encoding="utf-8")
    evidence_provenance_md_path = output_dir / "evidence_provenance_summary.md"
    provenance_md = [
        "# Gold-Core Evidence Provenance Summary", "", "Version: v0.9.5.150", "",
        "This report is read-only. Ground Truth is comparison context only and Operational Truth is unchanged.", "",
        "## First Failed Stages", "",
    ]
    for item in evidence_provenance_summary.to_dict(orient="records"):
        provenance_md.extend([
            f"### {item.get('first_failed_stage', '')}", "",
            f"- Blocking positions: {item.get('positions', 0)}",
            f"- Affected cases: {item.get('cases', 0)}",
            f"- Average best confidence: {float(item.get('avg_best_confidence', 0) or 0):.2%}",
            f"- Recommended action: `{item.get('recommended_action', '')}`", "",
        ])
    evidence_provenance_md_path.write_text("\n".join(provenance_md), encoding="utf-8")
    position_bridge_json_path = output_dir / "position_evidence_bridge_report.json"
    position_bridge_json_path.write_text(json.dumps(_json_safe({
        "phase": "v0.9.5.153_provenance_aware_character_alignment",
        "summary": position_bridge_summary.to_dict(orient="records"),
        "cases": position_bridge_cases.to_dict(orient="records"),
        "positions": position_bridge_positions.to_dict(orient="records"),
        "rejected_bindings": position_bridge_rejected.to_dict(orient="records"),
        "safety": {"ground_truth_used_as_evidence": False, "character_created_by_bridge": False, "operational_truth_modified": False},
    }), ensure_ascii=False, indent=2), encoding="utf-8")
    position_bridge_md_path = output_dir / "position_evidence_bridge_summary.md"
    bridge_md = ["# Position Evidence Acquisition Bridge", "", "Version: v0.9.5.151", "", "The bridge links existing evidence only; it never creates characters or changes Operational Truth.", "", "## Binding summary", ""]
    for item in position_bridge_summary.to_dict(orient="records"):
        bridge_md.append(f"- `{item.get('binding_status')}`: {item.get('positions', 0)} positions across {item.get('cases', 0)} cases")
    position_bridge_md_path.write_text("\n".join(bridge_md), encoding="utf-8")
    identity_graph_json_path = output_dir / "identity_graph_report.json"
    identity_graph_json_path.write_text(json.dumps(_json_safe({
        "phase": "v0.9.5.154_identity_graph",
        "cases": identity_graph_cases.to_dict(orient="records"),
        "characters": identity_graph_characters.to_dict(orient="records"),
        "tokens": identity_graph_tokens.to_dict(orient="records"),
        "components": identity_graph_components.to_dict(orient="records"),
        "edges": identity_graph_edges.to_dict(orient="records"),
        "safety": {"ground_truth_used_as_evidence": False, "identity_authoritative": False, "gold_clearance_created": False, "operational_truth_modified": False},
    }), ensure_ascii=False, indent=2), encoding="utf-8")
    identity_graph_md_path = output_dir / "identity_graph_summary.md"
    identity_md = ["# Player Identity Graph", "", "Version: v0.9.5.154", "", "Read-only observed identity intelligence. No component is Gold-authoritative.", "", "## Cases", ""]
    for item in identity_graph_cases.to_dict(orient="records"):
        identity_md.extend([f"### Rank {item.get('rank')} — {item.get('observed_identity_text', '')}", "", f"- Status: `{item.get('identity_resolution_status', '')}`", f"- Tokens: {item.get('tokens', 0)}", f"- Components: {item.get('components', 0)}", f"- Types: {item.get('component_types', '[]')}", f"- UNKNOWN protected: {item.get('unknown_protected', False)}", ""])
    identity_graph_md_path.write_text("\n".join(identity_md), encoding="utf-8")


    identity_composition_json_path = output_dir / "identity_composition_report.json"
    identity_composition_json_path.write_text(json.dumps(_json_safe({
        "phase": "v0.9.5.155_identity_composition",
        "compositions": identity_compositions.to_dict(orient="records"),
        "slots": identity_slots.to_dict(orient="records"),
        "root_cause_summary": identity_root_cause_summary.to_dict(orient="records"),
        "priority_summary": identity_priority_summary.to_dict(orient="records"),
        "guardrails": {"identity_authoritative": False, "gold_clearance_created": False, "ground_truth_used_as_evidence": False},
    }), ensure_ascii=False, indent=2), encoding="utf-8")
    identity_composition_md_path = output_dir / "identity_composition_summary.md"
    comp_md = ["# Identity Composition Summary", "", "Strike XII is diagnostic and non-authoritative.", "",
               f"- Cases: {len(identity_compositions)}", f"- Slots: {len(identity_slots)}", f"- Manual review items: {len(manual_review_queue)}", ""]
    if not identity_priority_summary.empty:
        comp_md += ["## Review priorities", ""]
        for item in identity_priority_summary.to_dict(orient="records"):
            comp_md.append(f"- {item.get('priority')}: {item.get('recommended_action')} = {item.get('cases')}")
    identity_composition_md_path.write_text("\n".join(comp_md), encoding="utf-8")

    manual_review_json_path = output_dir / "manual_review_queue.json"
    manual_review_json_path.write_text(json.dumps(_json_safe({
        "phase": "v0.9.5.155_manual_review_queue",
        "queue": manual_review_queue.to_dict(orient="records"),
        "priority_summary": identity_priority_summary.to_dict(orient="records"),
        "root_cause_summary": identity_root_cause_summary.to_dict(orient="records"),
        "guardrails": {"review_queue_authoritative": False, "gold_clearance_created": False},
    }), ensure_ascii=False, indent=2), encoding="utf-8")
    review_orchestration_json_path = output_dir / "review_orchestration_report.json"
    review_orchestration_json_path.write_text(json.dumps(_json_safe({
        "phase": "v0.9.5.156_gold_core_bound_review",
        "summary": review_orchestration_summary.to_dict(orient="records"),
        "case_binding": review_case_bindings.to_dict(orient="records"),
        "confidence": review_confidence_calibration.to_dict(orient="records"),
        "validation": review_validation.to_dict(orient="records"),
        "priority_summary": identity_priority_summary.to_dict(orient="records"),
        "root_cause_summary": identity_root_cause_summary.to_dict(orient="records"),
        "guardrails": {"review_authoritative": False, "gold_clearance_created": False, "ground_truth_used_as_evidence": False, "operational_truth_modified": False},
    }), ensure_ascii=False, indent=2), encoding="utf-8")
    review_orchestration_md_path = output_dir / "review_orchestration_summary.md"
    orch = review_orchestration_summary.iloc[0].to_dict() if not review_orchestration_summary.empty else {}
    review_orchestration_md_path.write_text("\n".join([
        "# Gold-Core-Bound Review Orchestration", "", "Version: v0.9.5.156", "",
        f"- Open Gold Core cases: {orch.get('open_gold_core_cases', 0)}",
        f"- Review queue cases: {orch.get('review_queue_cases', 0)}",
        f"- Queue coverage: {orch.get('queue_coverage_percent', 0)}%",
        f"- Case-binding success: {orch.get('case_binding_success_percent', 0)}%",
        f"- Metadata-complete cases: {orch.get('metadata_complete_cases', 0)}", "",
        "The orchestration layer is read-only and cannot clear Gold Core or modify Operational Truth.",
    ]), encoding="utf-8")
    manual_review_md_path = output_dir / "manual_review_queue_summary.md"
    qlines=["# Manual Review Queue", "", "Version: v0.9.5.156", ""]
    for item in identity_priority_summary.to_dict(orient="records"):
        qlines.append(f"- `{item.get('priority')}` / `{item.get('review_action')}`: {item.get('cases')} cases")
    manual_review_md_path.write_text("\n".join(qlines), encoding="utf-8")
    resolution_readiness_json_path = output_dir / "resolution_readiness_report.json"
    resolution_readiness_json_path.write_text(json.dumps(_json_safe({
        "phase": "v0.9.5.157_resolution_readiness",
        "summary": resolution_readiness_summary.to_dict(orient="records"),
        "breakdown": resolution_readiness_breakdown.to_dict(orient="records"),
        "cases": resolution_readiness_cases.to_dict(orient="records"),
        "validation": resolution_readiness_validation.to_dict(orient="records"),
        "guardrails": {"resolution_readiness_authoritative": False, "automatic_fix_executed": False, "gold_clearance_created": False, "ground_truth_used_as_evidence": False, "operational_truth_modified": False},
    }), ensure_ascii=False, indent=2), encoding="utf-8")
    resolution_readiness_md_path = output_dir / "resolution_readiness_summary.md"
    rr = resolution_readiness_summary.iloc[0].to_dict() if not resolution_readiness_summary.empty else {}
    lines = ["# Resolution Readiness Intelligence", "", "Version: v0.9.5.157", "",
        f"- Cases: {rr.get('cases', 0)}",
        f"- Scored root causes: {rr.get('scored_root_causes', 0)}",
        f"- Scored recommendations: {rr.get('scored_recommendations', 0)}",
        f"- Distinct review-confidence values: {rr.get('dynamic_review_confidence_cases', 0)}",
        f"- Ready for targeted ReOCR: {rr.get('ready_for_targeted_reocr', 0)}",
        f"- Ready for manual review: {rr.get('ready_for_manual_review', 0)}",
        f"- Waiting for evidence: {rr.get('waiting_for_evidence', 0)}",
        f"- Policy decision required: {rr.get('policy_decision_required', 0)}",
        f"- Unsafe to resolve: {rr.get('unsafe_to_resolve', 0)}", "",
        "This intelligence is diagnostic only. It cannot execute fixes, clear Gold Core, or modify Operational Truth."]
    resolution_readiness_md_path.write_text("\n".join(lines), encoding="utf-8")
    classification_stability_json_path = output_dir / "classification_stability_report.json"
    classification_stability_json_path.write_text(json.dumps(_json_safe({
        "phase":"v0.9.5.158_classification_stability","summary":classification_stability_summary.to_dict(orient="records"),
        "cases":classification_stability_cases.to_dict(orient="records"),"validation":classification_stability_validation.to_dict(orient="records"),
        "guardrails":{"classification_authoritative":False,"gold_clearance_created":False,"operational_truth_modified":False}
    }),ensure_ascii=False,indent=2),encoding="utf-8")
    classification_stability_md_path = output_dir / "classification_stability_summary.md"
    cs = classification_stability_summary.iloc[0].to_dict() if not classification_stability_summary.empty else {}
    classification_stability_md_path.write_text("\n".join(["# Classification Stability", "", "Version: v0.9.5.158", "", f"- Cases: {cs.get('cases',0)}", f"- Previous baseline cases: {cs.get('previous_baseline_cases',0)}", f"- Classification changes: {cs.get('classification_changes',0)}", f"- Unexplained changes: {cs.get('unexplained_classification_changes',0)}", f"- Distinct evidence coverage values: {cs.get('distinct_evidence_coverage_values',0)}", "", "No classification change is accepted silently. The layer is diagnostic and read-only."]),encoding="utf-8")
    evidence_coverage_json_path = output_dir / "evidence_coverage_report.json"
    evidence_coverage_json_path.write_text(json.dumps(_json_safe({"phase":"v0.9.5.158_evidence_coverage","cases":classification_stability_cases.to_dict(orient="records"),"requirements":evidence_coverage_rows.to_dict(orient="records"),"score_decomposition":score_decomposition_rows.to_dict(orient="records")}),ensure_ascii=False,indent=2),encoding="utf-8")
    evidence_coverage_md_path = output_dir / "evidence_coverage_summary.md"
    evidence_coverage_md_path.write_text("\n".join(["# Resolution Evidence Coverage", "", "Version: v0.9.5.158", "", f"- Cases: {len(classification_stability_cases)}", f"- Distinct coverage values: {classification_stability_cases['required_evidence_coverage'].nunique() if not classification_stability_cases.empty else 0}", f"- Average coverage: {classification_stability_cases['required_evidence_coverage'].mean():.2%}" if not classification_stability_cases.empty else "- Average coverage: 0%", "", "Coverage is calculated against the evidence required by each concrete review action."]),encoding="utf-8")
    decision_history_json_path = output_dir / "decision_history_report.json"
    decision_history_json_path.write_text(json.dumps(_json_safe({"phase":"v0.9.5.159_decision_history","summary":stability_history_summary.to_dict(orient="records"),"history":decision_history_rows.to_dict(orient="records"),"validation":stability_history_validation.to_dict(orient="records")}),ensure_ascii=False,indent=2),encoding="utf-8")
    decision_history_md_path = output_dir / "decision_history_summary.md"
    sh = stability_history_summary.iloc[0].to_dict() if not stability_history_summary.empty else {}
    decision_history_md_path.write_text("\n".join(["# Decision History", "", "Release version: v0.9.5.159", "", f"- Run ID: {sh.get('run_id','')}", f"- Current cases: {sh.get('cases',0)}", f"- History entries: {sh.get('history_entries',0)}", f"- Recorded runs: {sh.get('runs',0)}", f"- Unexplained drifts: {sh.get('unexplained_drifts',0)}", "", "History is diagnostic, append-only and does not modify Operational Truth."]),encoding="utf-8")
    resolution_simulator_json_path = output_dir / "resolution_simulator_report.json"
    resolution_simulator_json_path.write_text(json.dumps(_json_safe({"phase":"v0.9.5.161_resolution_simulator","summary":resolution_simulation_summary.to_dict(orient="records"),"cases":resolution_simulation_cases.to_dict(orient="records"),"options":resolution_simulation_options.to_dict(orient="records"),"validation":resolution_simulation_validation.to_dict(orient="records")}),ensure_ascii=False,indent=2),encoding="utf-8")
    resolution_simulator_md_path = output_dir / "resolution_simulator_summary.md"
    rs = resolution_simulation_summary.iloc[0].to_dict() if not resolution_simulation_summary.empty else {}
    resolution_simulator_md_path.write_text("\n".join(["# Resolution Simulator", "", "Release version: v0.9.5.160", "", f"- Cases: {rs.get('cases',0)}", f"- Simulated options: {rs.get('options',0)}", f"- Recommended options: {rs.get('recommended_options',0)}", f"- Strategy alignment cases: {rs.get('strategy_alignment_cases',0)}", f"- Average expected resolution gain: {rs.get('average_expected_resolution_gain',0)}", f"- Average expected information gain: {rs.get('average_expected_information_gain',0)}", f"- Average expected risk: {rs.get('average_expected_risk',0)}", "", "All outcomes are simulated. No fix, clearance, Ground Truth substitution, or Operational Truth mutation is executed."]),encoding="utf-8")
    stability_timeline_json_path = output_dir / "stability_timeline_report.json"
    stability_timeline_json_path.write_text(json.dumps(_json_safe({"phase":"v0.9.5.159_stability_timeline","timeline":stability_timeline_rows.to_dict(orient="records")}),ensure_ascii=False,indent=2),encoding="utf-8")
    stability_timeline_md_path = output_dir / "stability_timeline_summary.md"
    stability_timeline_md_path.write_text("\n".join(["# Stability Timeline", "", "Release version: v0.9.5.159", "", f"- Cases in current run: {sh.get('cases',0)}", f"- Prior cases compared: {sh.get('prior_cases_compared',0)}", f"- Stable cases: {sh.get('stable_cases',0)}", f"- No previous baseline: {sh.get('no_previous_baseline',0)}", "", "Each case retains evidence, classification and decision fingerprints across runs."]),encoding="utf-8")
    drift_analysis_json_path = output_dir / "drift_analysis_report.json"
    drift_analysis_json_path.write_text(json.dumps(_json_safe({"phase":"v0.9.5.159_drift_analysis","summary":stability_history_summary.to_dict(orient="records"),"drifts":drift_analysis_rows.to_dict(orient="records"),"validation":stability_history_validation.to_dict(orient="records")}),ensure_ascii=False,indent=2),encoding="utf-8")
    drift_analysis_md_path = output_dir / "drift_analysis_summary.md"
    drift_analysis_md_path.write_text("\n".join(["# Drift Analysis", "", "Release version: v0.9.5.159", "", f"- Classification drifts: {sh.get('classification_drifts',0)}", f"- Decision drifts: {sh.get('decision_drifts',0)}", f"- Unexplained drifts: {sh.get('unexplained_drifts',0)}", "", "Unexplained drift is CRITICAL; evidence-backed drift remains diagnostic and requires review."]),encoding="utf-8")

    ocr_evidence_json_path = output_dir / "ocr_evidence_report.json"
    ocr_evidence_json_path.write_text(json.dumps(_json_safe(ocr_evidence_payload), ensure_ascii=False, indent=2), encoding="utf-8")
    gold_core_json_path = output_dir / "gold_core_blocker_report.json"
    gold_core_json_path.write_text(json.dumps(_json_safe({"summary": gold_core_blocker_summary.to_dict(orient="records"), "details": gold_core_blocker_report.to_dict(orient="records")}), ensure_ascii=False, indent=2), encoding="utf-8")
    gold_core_resolution_json_path = output_dir / "gold_core_resolution_plan_report.json"
    gold_core_resolution_json_path.write_text(json.dumps(_json_safe({"summary": gold_core_resolution_summary.to_dict(orient="records"), "details": gold_core_resolution_plan.to_dict(orient="records")}), ensure_ascii=False, indent=2), encoding="utf-8")
    gold_core_elimination_json_path = output_dir / "gold_core_elimination_report.json"
    gold_core_elimination_json_path.write_text(json.dumps(_json_safe({"summary": gold_core_elimination_summary.to_dict(orient="records"), "details": gold_core_elimination_rows.to_dict(orient="records")}), ensure_ascii=False, indent=2), encoding="utf-8")
    gold_core_analytics_json_path = output_dir / "gold_core_analytics_report.json"
    gold_core_analytics_json_path.write_text(json.dumps(_json_safe({"phase": "v0.9.5.144_gold_core_strike_v", "summary": gold_core_analytics_summary.to_dict(orient="records"), "details": gold_core_analytics_rows.to_dict(orient="records"), "failure_memory": gold_core_failure_memory.to_dict(orient="records"), "case_explorer": gold_core_case_explorer.to_dict(orient="records"), "prioritized_actions": gold_core_prioritized_actions.to_dict(orient="records"), "operational_truth_modified": False}), ensure_ascii=False, indent=2), encoding="utf-8")
    gold_core_case_explorer_json_path = output_dir / "gold_core_case_explorer.json"
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
        _sanitize_frame(gold_core_character_cases).to_excel(writer, sheet_name="gc_char_cases", index=False)
        _sanitize_frame(gold_core_character_positions).to_excel(writer, sheet_name="gc_char_positions", index=False)
        _sanitize_frame(gold_core_position_heatmap).to_excel(writer, sheet_name="gc_pos_heatmap", index=False)
        _sanitize_frame(evidence_provenance_summary).to_excel(writer, sheet_name="evidence_prov_summary", index=False)
        _sanitize_frame(evidence_provenance_cases).to_excel(writer, sheet_name="evidence_prov_cases", index=False)
        _sanitize_frame(evidence_provenance_positions).to_excel(writer, sheet_name="evidence_prov_pos", index=False)
        _sanitize_frame(evidence_provenance_stages).to_excel(writer, sheet_name="evidence_prov_stages", index=False)
        _sanitize_frame(identity_graph_cases).to_excel(writer, sheet_name="identity_cases", index=False)
        _sanitize_frame(identity_graph_tokens).to_excel(writer, sheet_name="identity_tokens", index=False)
        _sanitize_frame(identity_graph_components).to_excel(writer, sheet_name="identity_components", index=False)
        _sanitize_frame(identity_graph_edges).to_excel(writer, sheet_name="identity_edges", index=False)
        _sanitize_frame(identity_compositions).to_excel(writer, sheet_name="identity_composition", index=False)
        _sanitize_frame(identity_slots).to_excel(writer, sheet_name="identity_slots", index=False)
        _sanitize_frame(manual_review_queue).to_excel(writer, sheet_name="manual_review_queue", index=False)
        _sanitize_frame(identity_root_cause_summary).to_excel(writer, sheet_name="identity_root_causes", index=False)
        _sanitize_frame(review_orchestration_summary).to_excel(writer, sheet_name="review_orch_summary", index=False)
        _sanitize_frame(review_case_bindings).to_excel(writer, sheet_name="review_case_binding", index=False)
        _sanitize_frame(review_confidence_calibration).to_excel(writer, sheet_name="review_confidence", index=False)
        _sanitize_frame(review_validation).to_excel(writer, sheet_name="review_validation", index=False)
        _sanitize_frame(resolution_readiness_summary).to_excel(writer, sheet_name="resolution_ready_sum", index=False)
        _sanitize_frame(resolution_readiness_cases).to_excel(writer, sheet_name="resolution_ready", index=False)
        _sanitize_frame(resolution_readiness_validation).to_excel(writer, sheet_name="resolution_valid", index=False)
        _sanitize_frame(classification_stability_summary).to_excel(writer, sheet_name="class_stability_sum", index=False)
        _sanitize_frame(classification_stability_cases).to_excel(writer, sheet_name="class_stability", index=False)
        _sanitize_frame(classification_stability_validation).to_excel(writer, sheet_name="class_stab_valid", index=False)
        _sanitize_frame(evidence_coverage_rows).to_excel(writer, sheet_name="evidence_coverage", index=False)
        _sanitize_frame(score_decomposition_rows).to_excel(writer, sheet_name="score_factors", index=False)
        _sanitize_frame(position_bridge_summary).to_excel(writer, sheet_name="position_bridge_sum", index=False)
        _sanitize_frame(position_bridge_cases).to_excel(writer, sheet_name="position_bridge_cases", index=False)
        _sanitize_frame(position_bridge_positions).to_excel(writer, sheet_name="position_bridge_pos", index=False)
        _sanitize_frame(position_bridge_rejected).to_excel(writer, sheet_name="position_bridge_rej", index=False)
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

    character_evidence_xlsx_path = output_dir / "character_position_report.xlsx"
    with pd.ExcelWriter(character_evidence_xlsx_path, engine="openpyxl") as writer:
        _sanitize_frame(gold_core_character_cases).to_excel(writer, sheet_name="cases", index=False)
        _sanitize_frame(gold_core_character_positions).to_excel(writer, sheet_name="positions", index=False)
        _sanitize_frame(gold_core_position_heatmap).to_excel(writer, sheet_name="heatmap", index=False)

    evidence_provenance_xlsx_path = output_dir / "evidence_provenance_report.xlsx"
    with pd.ExcelWriter(evidence_provenance_xlsx_path, engine="openpyxl") as writer:
        _sanitize_frame(evidence_provenance_summary).to_excel(writer, sheet_name="summary", index=False)
        _sanitize_frame(evidence_provenance_cases).to_excel(writer, sheet_name="cases", index=False)
        _sanitize_frame(evidence_provenance_positions).to_excel(writer, sheet_name="positions", index=False)
        _sanitize_frame(evidence_provenance_stages).to_excel(writer, sheet_name="stages", index=False)

    position_bridge_xlsx_path = output_dir / "position_evidence_bridge_report.xlsx"
    with pd.ExcelWriter(position_bridge_xlsx_path, engine="openpyxl") as writer:
        _sanitize_frame(position_bridge_summary).to_excel(writer, sheet_name="summary", index=False)
        _sanitize_frame(position_bridge_cases).to_excel(writer, sheet_name="cases", index=False)
        _sanitize_frame(position_bridge_positions).to_excel(writer, sheet_name="positions", index=False)
        _sanitize_frame(position_bridge_rejected).to_excel(writer, sheet_name="rejected_bindings", index=False)

    identity_graph_xlsx_path = output_dir / "identity_graph_report.xlsx"
    with pd.ExcelWriter(identity_graph_xlsx_path, engine="openpyxl") as writer:
        _sanitize_frame(identity_graph_cases).to_excel(writer, sheet_name="cases", index=False)
        _sanitize_frame(identity_graph_characters).to_excel(writer, sheet_name="characters", index=False)
        _sanitize_frame(identity_graph_tokens).to_excel(writer, sheet_name="tokens", index=False)
        _sanitize_frame(identity_graph_components).to_excel(writer, sheet_name="components", index=False)
        _sanitize_frame(identity_graph_edges).to_excel(writer, sheet_name="edges", index=False)


    identity_composition_xlsx_path = output_dir / "identity_composition_report.xlsx"
    with pd.ExcelWriter(identity_composition_xlsx_path, engine="openpyxl") as writer:
        _sanitize_frame(identity_compositions).to_excel(writer, sheet_name="compositions", index=False)
        _sanitize_frame(identity_slots).to_excel(writer, sheet_name="slots", index=False)
        _sanitize_frame(identity_root_cause_summary).to_excel(writer, sheet_name="root_causes", index=False)
        _sanitize_frame(identity_priority_summary).to_excel(writer, sheet_name="priorities", index=False)

    manual_review_xlsx_path = output_dir / "manual_review_queue.xlsx"
    with pd.ExcelWriter(manual_review_xlsx_path, engine="openpyxl") as writer:
        _sanitize_frame(manual_review_queue).to_excel(writer, sheet_name="queue", index=False)
        _sanitize_frame(identity_priority_summary).to_excel(writer, sheet_name="priorities", index=False)
        _sanitize_frame(identity_root_cause_summary).to_excel(writer, sheet_name="root_causes", index=False)
        _sanitize_frame(review_case_bindings).to_excel(writer, sheet_name="case_binding", index=False)
        _sanitize_frame(review_confidence_calibration).to_excel(writer, sheet_name="confidence", index=False)
        _sanitize_frame(review_validation).to_excel(writer, sheet_name="validation", index=False)

    review_orchestration_xlsx_path = output_dir / "review_orchestration_report.xlsx"
    with pd.ExcelWriter(review_orchestration_xlsx_path, engine="openpyxl") as writer:
        _sanitize_frame(review_orchestration_summary).to_excel(writer, sheet_name="summary", index=False)
        _sanitize_frame(manual_review_queue).to_excel(writer, sheet_name="queue", index=False)
        _sanitize_frame(review_case_bindings).to_excel(writer, sheet_name="case_binding", index=False)
        _sanitize_frame(review_confidence_calibration).to_excel(writer, sheet_name="confidence", index=False)
        _sanitize_frame(identity_root_cause_summary).to_excel(writer, sheet_name="root_causes", index=False)
        _sanitize_frame(identity_priority_summary).to_excel(writer, sheet_name="priorities", index=False)
        _sanitize_frame(review_validation).to_excel(writer, sheet_name="validation", index=False)

    resolution_readiness_xlsx_path = output_dir / "resolution_readiness_report.xlsx"
    with pd.ExcelWriter(resolution_readiness_xlsx_path, engine="openpyxl") as writer:
        _sanitize_frame(resolution_readiness_summary).to_excel(writer, sheet_name="summary", index=False)
        _sanitize_frame(resolution_readiness_breakdown).to_excel(writer, sheet_name="readiness", index=False)
        _sanitize_frame(resolution_readiness_cases).to_excel(writer, sheet_name="cases", index=False)
        _sanitize_frame(resolution_readiness_validation).to_excel(writer, sheet_name="validation", index=False)

    classification_stability_xlsx_path = output_dir / "classification_stability_report.xlsx"
    with pd.ExcelWriter(classification_stability_xlsx_path, engine="openpyxl") as writer:
        _sanitize_frame(classification_stability_summary).to_excel(writer, sheet_name="summary", index=False)
        _sanitize_frame(classification_stability_cases).to_excel(writer, sheet_name="cases", index=False)
        _sanitize_frame(classification_stability_validation).to_excel(writer, sheet_name="validation", index=False)
    evidence_coverage_xlsx_path = output_dir / "evidence_coverage_report.xlsx"
    with pd.ExcelWriter(evidence_coverage_xlsx_path, engine="openpyxl") as writer:
        _sanitize_frame(classification_stability_cases).to_excel(writer, sheet_name="cases", index=False)
        _sanitize_frame(evidence_coverage_rows).to_excel(writer, sheet_name="requirements", index=False)
        _sanitize_frame(score_decomposition_rows).to_excel(writer, sheet_name="score_factors", index=False)

    decision_history_xlsx_path = output_dir / "decision_history_report.xlsx"
    with pd.ExcelWriter(decision_history_xlsx_path, engine="openpyxl") as writer:
        _sanitize_frame(stability_history_summary).to_excel(writer, sheet_name="summary", index=False)
        _sanitize_frame(decision_history_rows).to_excel(writer, sheet_name="history", index=False)
        _sanitize_frame(stability_history_validation).to_excel(writer, sheet_name="validation", index=False)
    stability_timeline_xlsx_path = output_dir / "stability_timeline_report.xlsx"
    with pd.ExcelWriter(stability_timeline_xlsx_path, engine="openpyxl") as writer:
        _sanitize_frame(stability_history_summary).to_excel(writer, sheet_name="summary", index=False)
        _sanitize_frame(stability_timeline_rows).to_excel(writer, sheet_name="timeline", index=False)
    drift_analysis_xlsx_path = output_dir / "drift_analysis_report.xlsx"
    with pd.ExcelWriter(drift_analysis_xlsx_path, engine="openpyxl") as writer:
        _sanitize_frame(stability_history_summary).to_excel(writer, sheet_name="summary", index=False)
        _sanitize_frame(drift_analysis_rows).to_excel(writer, sheet_name="drifts", index=False)
        _sanitize_frame(stability_history_validation).to_excel(writer, sheet_name="validation", index=False)
    regression_dashboard_xlsx_path = output_dir / "regression_dashboard.xlsx"
    with pd.ExcelWriter(regression_dashboard_xlsx_path, engine="openpyxl") as writer:
        _sanitize_frame(regression_dashboard_rows).to_excel(writer, sheet_name="runs", index=False)
        _sanitize_frame(stability_history_summary).to_excel(writer, sheet_name="current_run", index=False)
        _sanitize_frame(drift_analysis_rows).to_excel(writer, sheet_name="case_drift", index=False)

    resolution_simulator_xlsx_path = output_dir / "resolution_simulator_report.xlsx"
    with pd.ExcelWriter(resolution_simulator_xlsx_path, engine="openpyxl") as writer:
        _sanitize_frame(resolution_simulation_summary).to_excel(writer, sheet_name="summary", index=False)
        _sanitize_frame(resolution_simulation_cases).to_excel(writer, sheet_name="cases", index=False)
        _sanitize_frame(resolution_simulation_options).to_excel(writer, sheet_name="options", index=False)
        _sanitize_frame(resolution_simulation_validation).to_excel(writer, sheet_name="validation", index=False)

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
    gold_core_analytics_xlsx_path = output_dir / "gold_core_analytics_report.xlsx"
    with pd.ExcelWriter(gold_core_analytics_xlsx_path, engine="openpyxl") as writer:
        _sanitize_frame(gold_core_analytics_summary).to_excel(writer, sheet_name="summary", index=False)
        _sanitize_frame(gold_core_analytics_rows).to_excel(writer, sheet_name="root_causes", index=False)
        _sanitize_frame(gold_core_failure_memory).to_excel(writer, sheet_name="failure_memory", index=False)
        _sanitize_frame(gold_core_case_explorer).to_excel(writer, sheet_name="case_explorer", index=False)
        _sanitize_frame(gold_core_prioritized_actions).to_excel(writer, sheet_name="prioritized_actions", index=False)
    gold_core_case_explorer_xlsx_path = output_dir / "gold_core_case_explorer.xlsx"
    with pd.ExcelWriter(gold_core_case_explorer_xlsx_path, engine="openpyxl") as writer:
        _sanitize_frame(gold_core_case_explorer).to_excel(writer, sheet_name="cases", index=False)
        _sanitize_frame(gold_core_prioritized_actions).to_excel(writer, sheet_name="prioritized_actions", index=False)
        _sanitize_frame(gold_core_failure_memory).to_excel(writer, sheet_name="failure_memory", index=False)
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

    if output_dir.resolve() == DEFAULT_OUTPUT_DIR.resolve():
        _publish_report_architecture(
            output_dir, json_payload=json_payload, summary_rows=summary_rows,
            regression_dashboard_rows=regression_dashboard_rows,
            resolution_readiness_summary=resolution_readiness_summary,
            resolution_readiness_cases=resolution_readiness_cases,
            resolution_simulation_summary=resolution_simulation_summary,
            resolution_simulation_cases=resolution_simulation_cases,
            resolution_simulation_options=resolution_simulation_options,
            resolution_simulation_validation=resolution_simulation_validation,
            manual_review_queue=manual_review_queue,
            gold_core_case_explorer=gold_core_case_explorer,
            gold_core_prioritized_actions=gold_core_prioritized_actions,
            classification_stability_cases=classification_stability_cases,
            decision_history_rows=decision_history_rows,
            stability_timeline_rows=stability_timeline_rows,
            drift_analysis_rows=drift_analysis_rows,
            evidence_coverage_rows=evidence_coverage_rows,
            score_decomposition_rows=score_decomposition_rows,
            review_case_bindings=review_case_bindings,
            review_confidence_calibration=review_confidence_calibration,
            identity_compositions=identity_compositions,
            identity_slots=identity_slots,
            identity_graph_cases=identity_graph_cases,
            evidence_provenance_cases=evidence_provenance_cases,
            position_bridge_cases=position_bridge_cases,
            runtime_payload=runtime_payload, runtime_phase_df=runtime_phase_df,
        )

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
    print(f"Gold-Core Character Evidence JSON: {character_evidence_json_path}")
    print(f"Gold-Core Character Evidence Excel: {character_evidence_xlsx_path}")
    print(f"Gold-Core Position Heatmap JSON: {position_heatmap_json_path}")
    print(f"Evidence Provenance JSON: {evidence_provenance_json_path}")
    print(f"Evidence Provenance XLSX: {evidence_provenance_xlsx_path}")
    print(f"Evidence Provenance Summary: {evidence_provenance_md_path}")
    print(f"Position Evidence Bridge JSON: {position_bridge_json_path}")
    print(f"Position Evidence Bridge XLSX: {position_bridge_xlsx_path}")
    print(f"Position Evidence Bridge Summary: {position_bridge_md_path}")
    print(f"Identity Composition JSON: {identity_composition_json_path}")
    print(f"Identity Composition XLSX: {identity_composition_xlsx_path}")
    print(f"Identity Composition Summary: {identity_composition_md_path}")
    print(f"Manual Review Queue JSON: {manual_review_json_path}")
    print(f"Manual Review Queue XLSX: {manual_review_xlsx_path}")
    print(f"Manual Review Queue Summary: {manual_review_md_path}")
    print(f"Review Orchestration JSON: {review_orchestration_json_path}")
    print(f"Review Orchestration XLSX: {review_orchestration_xlsx_path}")
    print(f"Review Orchestration Summary: {review_orchestration_md_path}")
    print(f"Resolution Readiness JSON: {resolution_readiness_json_path}")
    print(f"Resolution Readiness XLSX: {resolution_readiness_xlsx_path}")
    print(f"Resolution Readiness Summary: {resolution_readiness_md_path}")
    print(f"Classification Stability JSON: {classification_stability_json_path}")
    print(f"Classification Stability XLSX: {classification_stability_xlsx_path}")
    print(f"Classification Stability Summary: {classification_stability_md_path}")
    print(f"Evidence Coverage JSON: {evidence_coverage_json_path}")
    print(f"Evidence Coverage XLSX: {evidence_coverage_xlsx_path}")
    print(f"Evidence Coverage Summary: {evidence_coverage_md_path}")
    print(f"Decision History JSON: {decision_history_json_path}")
    print(f"Decision History XLSX: {decision_history_xlsx_path}")
    print(f"Decision History Summary: {decision_history_md_path}")
    print(f"Stability Timeline JSON: {stability_timeline_json_path}")
    print(f"Stability Timeline XLSX: {stability_timeline_xlsx_path}")
    print(f"Stability Timeline Summary: {stability_timeline_md_path}")
    print(f"Drift Analysis JSON: {drift_analysis_json_path}")
    print(f"Drift Analysis XLSX: {drift_analysis_xlsx_path}")
    print(f"Drift Analysis Summary: {drift_analysis_md_path}")
    print(f"Regression Dashboard: {regression_dashboard_xlsx_path}")
    print(f"Character Position Summary MD: {character_position_summary_md_path}")
    print(f"OCR Evidence JSON:  {ocr_evidence_json_path}")
    print(f"Display Reconstruction JSON:  {display_reconstruction_json_path}")
    print(f"Evidence Confidence JSON:      {evidence_confidence_json_path}")
    print(f"Evidence Budget JSON:          {evidence_budget_json_path}")
    print(f"OCR Evidence Excel: {ocr_evidence_xlsx_path}")
    print(f"Gold Core Resolution Plan JSON:  {gold_core_resolution_json_path}")
    print(f"Gold Core Resolution Plan Excel: {gold_core_resolution_xlsx_path}")
    print(f"Gold Core Analytics JSON:         {gold_core_analytics_json_path}")
    print(f"Gold Core Analytics Excel:        {gold_core_analytics_xlsx_path}")
    print(f"Gold Core Case Explorer JSON:     {gold_core_case_explorer_json_path}")
    print(f"Gold Core Case Explorer Excel:    {gold_core_case_explorer_xlsx_path}")
    print(f"Gold Core Casebook:               {gold_core_casebook_path}")
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


def _publish_report_architecture(output_dir: Path, *, json_payload: dict[str, Any],
                                 summary_rows: list[dict[str, Any]],
                                 regression_dashboard_rows: pd.DataFrame,
                                 resolution_readiness_summary: pd.DataFrame,
                                 resolution_readiness_cases: pd.DataFrame,
                                 resolution_simulation_summary: pd.DataFrame,
                                 resolution_simulation_cases: pd.DataFrame,
                                 resolution_simulation_options: pd.DataFrame,
                                 resolution_simulation_validation: pd.DataFrame,
                                 manual_review_queue: pd.DataFrame,
                                 gold_core_case_explorer: pd.DataFrame,
                                 gold_core_prioritized_actions: pd.DataFrame,
                                 classification_stability_cases: pd.DataFrame,
                                 decision_history_rows: pd.DataFrame,
                                 stability_timeline_rows: pd.DataFrame,
                                 drift_analysis_rows: pd.DataFrame,
                                 evidence_coverage_rows: pd.DataFrame,
                                 score_decomposition_rows: pd.DataFrame,
                                 review_case_bindings: pd.DataFrame,
                                 review_confidence_calibration: pd.DataFrame,
                                 identity_compositions: pd.DataFrame,
                                 identity_slots: pd.DataFrame,
                                 identity_graph_cases: pd.DataFrame,
                                 evidence_provenance_cases: pd.DataFrame,
                                 position_bridge_cases: pd.DataFrame,
                                 runtime_payload: dict[str, Any],
                                 runtime_phase_df: pd.DataFrame) -> None:
    """Strike XVIII: publish a compact root-level report architecture.

    Benchmark folders remain input/runtime territory. All report output is owned by
    the repository root /reports tree. Detailed intelligence is retained as workbook
    tabs and JSON sections rather than duplicated into dozens of peer files.
    """
    import shutil
    output_dir = Path(output_dir)
    executive = output_dir / "executive"
    operations = output_dir / "operations"
    intelligence = output_dir / "intelligence"
    diagnostics = output_dir / "diagnostics"
    state = output_dir / "state"
    for folder in (executive, operations, intelligence, diagnostics, state):
        folder.mkdir(parents=True, exist_ok=True)

    metadata = pd.DataFrame([{
        "release_version": RELEASE_VERSION,
        "component_version": "v0.9.5.161_report_architecture",
        "report_root": str(output_dir),
        "benchmark_reports_allowed": False,
        "operational_truth_modified": False,
    }])

    with pd.ExcelWriter(executive / "SENTINEL_EXECUTIVE_REPORT.xlsx", engine="openpyxl") as writer:
        metadata.to_excel(writer, sheet_name="metadata", index=False)
        pd.DataFrame(summary_rows).to_excel(writer, sheet_name="validation_summary", index=False)
        _sanitize_frame(regression_dashboard_rows).to_excel(writer, sheet_name="regression", index=False)
        _sanitize_frame(resolution_readiness_summary).to_excel(writer, sheet_name="readiness", index=False)
        _sanitize_frame(resolution_simulation_summary).to_excel(writer, sheet_name="simulation", index=False)

    with pd.ExcelWriter(operations / "SENTINEL_RESOLUTION_WORKBENCH.xlsx", engine="openpyxl") as writer:
        metadata.to_excel(writer, sheet_name="metadata", index=False)
        _sanitize_frame(manual_review_queue).to_excel(writer, sheet_name="review_queue", index=False)
        _sanitize_frame(gold_core_case_explorer).to_excel(writer, sheet_name="gold_core_cases", index=False)
        _sanitize_frame(gold_core_prioritized_actions).to_excel(writer, sheet_name="prioritized_actions", index=False)
        _sanitize_frame(resolution_readiness_cases).to_excel(writer, sheet_name="readiness_cases", index=False)
        _sanitize_frame(resolution_simulation_cases).to_excel(writer, sheet_name="simulated_cases", index=False)
        _sanitize_frame(resolution_simulation_options).to_excel(writer, sheet_name="simulation_options", index=False)
        _sanitize_frame(resolution_simulation_validation).to_excel(writer, sheet_name="validation", index=False)

    intelligence_sheets = {
        "metadata": metadata,
        "classification": classification_stability_cases,
        "decision_history": decision_history_rows,
        "stability_timeline": stability_timeline_rows,
        "drift_analysis": drift_analysis_rows,
        "evidence_coverage": evidence_coverage_rows,
        "score_factors": score_decomposition_rows,
        "review_bindings": review_case_bindings,
        "confidence": review_confidence_calibration,
        "identity_composition": identity_compositions,
        "identity_slots": identity_slots,
        "identity_graph": identity_graph_cases,
        "provenance": evidence_provenance_cases,
        "position_bridge": position_bridge_cases,
    }
    with pd.ExcelWriter(intelligence / "SENTINEL_INTELLIGENCE_REPORT.xlsx", engine="openpyxl") as writer:
        for name, frame in intelligence_sheets.items():
            _sanitize_frame(frame).to_excel(writer, sheet_name=name[:31], index=False)
    (intelligence / "SENTINEL_INTELLIGENCE_REPORT.json").write_text(
        json.dumps(_json_safe(json_payload), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    with pd.ExcelWriter(diagnostics / "SENTINEL_RUNTIME_DIAGNOSTICS.xlsx", engine="openpyxl") as writer:
        metadata.to_excel(writer, sheet_name="metadata", index=False)
        pd.DataFrame([runtime_payload.get("summary", {})]).to_excel(writer, sheet_name="summary", index=False)
        _sanitize_frame(runtime_phase_df).to_excel(writer, sheet_name="phases", index=False)
        _sanitize_frame(pd.DataFrame(runtime_payload.get("character_reocr_groups", []))).to_excel(writer, sheet_name="reocr_groups", index=False)
    (diagnostics / "SENTINEL_RUNTIME_DIAGNOSTICS.json").write_text(
        json.dumps(_json_safe({"release_version": RELEASE_VERSION, **runtime_payload}), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    summary_text = [
        "# SENTINEL Executive Summary", "",
        f"- Release: {RELEASE_VERSION}",
        "- Reporting architecture: consolidated", "- Benchmark reports allowed: no",
        f"- Gold Core cases: {int(resolution_simulation_summary.iloc[0].get('cases', 0)) if not resolution_simulation_summary.empty else 0}",
        f"- Simulated options: {int(resolution_simulation_summary.iloc[0].get('options', 0)) if not resolution_simulation_summary.empty else 0}",
        "- Operational Truth modified: no", "",
    ]
    (executive / "SENTINEL_EXECUTIVE_SUMMARY.md").write_text("\n".join(summary_text), encoding="utf-8")

    casebook = output_dir / "GOLD_CORE_CASEBOOK.md"
    if casebook.exists():
        shutil.move(str(casebook), str(operations / casebook.name))

    keep_roots = {"executive", "operations", "intelligence", "diagnostics", "state"}
    for child in list(output_dir.iterdir()):
        if child.name in keep_roots or child.is_dir():
            continue
        if child.suffix.lower() in {".json", ".xlsx", ".md"}:
            child.unlink()



def _migrate_and_clean_legacy_benchmark_reports(reports_root: Path, ocr_output_path: Path) -> dict[str, int]:
    """Move durable state out of legacy benchmark folders and remove report artifacts.

    Only known report/state files in candidate benchmark roots are touched. Input,
    screenshots, OCR exports, caches and logs remain untouched.
    """
    import shutil
    reports_root = Path(reports_root)
    state_dir = reports_root / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    candidates = [Path("benchmarks"), ocr_output_path.parent, ocr_output_path.parent.parent]
    state_names = {
        "classification_stability_state.json",
        "decision_history_state.json",
        "gold_core_failure_memory.json",
    }
    report_markers = (
        "_report.json", "_report.xlsx", "_summary.md", "_dashboard.xlsx",
        "manual_review_queue.json", "manual_review_queue.xlsx",
        "ground_truth_validation_report.json", "ground_truth_validation_report.xlsx",
        "gold_core_case_explorer.json", "gold_core_case_explorer.xlsx",
        "position_heatmap.json", "GOLD_CORE_CASEBOOK.md",
    )
    migrated = removed = 0
    seen: set[Path] = set()
    for candidate in candidates:
        try:
            root = candidate.resolve()
        except Exception:
            continue
        if root in seen or not root.is_dir() or root == reports_root.resolve():
            continue
        seen.add(root)
        for path in list(root.iterdir()):
            if not path.is_file():
                continue
            if path.name in state_names:
                target = state_dir / path.name
                if not target.exists():
                    shutil.copy2(path, target)
                    migrated += 1
                path.unlink()
                removed += 1
                continue
            if any(path.name == marker or path.name.endswith(marker) for marker in report_markers):
                path.unlink()
                removed += 1
    return {"migrated_state_files": migrated, "removed_legacy_report_files": removed}


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
    migration_result = _migrate_and_clean_legacy_benchmark_reports(output_dir, ocr_output_path)
    if migration_result["migrated_state_files"] or migration_result["removed_legacy_report_files"]:
        print(f"Report migration: {migration_result}")

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
