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




def _apply_alignment_guard(detail: pd.DataFrame) -> pd.DataFrame:
    """Separate contextual alignment gaps from true character fidelity work.

    Contextual inferences are useful for recall/read-only gap explanation, but
    they are not row-level OCR matches. Comparing their Ground Truth identity
    against the rejected neighbouring OCR row creates false Character Re-OCR
    targets such as K9 Thunder vs YUNS.
    """
    if detail.empty:
        return detail
    guarded = detail.copy()
    inference_mask = guarded["match_method"].astype(str).str.startswith("inference_") | (guarded["failure_class"].astype(str) == "inferred_context_gap")
    guarded["alignment_guard_status"] = "row_alignment_observed"
    guarded.loc[inference_mask, "alignment_guard_status"] = "context_gap_no_character_verification"
    guarded["alignment_safe_for_character_verification"] = ~inference_mask

    if inference_mask.any():
        guarded.loc[inference_mask, "character_verification_candidate"] = False
        guarded.loc[inference_mask, "high_value_character_verification"] = False
        guarded.loc[inference_mask, "character_verification_reasons"] = "alignment_context_gap_not_character_drift"
        guarded.loc[inference_mask, "character_verification_targets"] = "[]"
        guarded.loc[inference_mask, "player_name_character_verification_targets"] = "[]"
        guarded.loc[inference_mask, "alliance_tag_character_verification_targets"] = "[]"
        guarded.loc[inference_mask, "character_reocr_status"] = "not_requested_alignment_context_gap"
        guarded.loc[inference_mask, "character_reocr_targets"] = 0
        guarded.loc[inference_mask, "character_reocr_verified_expected"] = 0
        guarded.loc[inference_mask, "character_reocr_verified_observed"] = 0
        guarded.loc[inference_mask, "character_reocr_unresolved"] = 0
        guarded.loc[inference_mask, "character_reocr_evidence"] = "[]"
        guarded.loc[inference_mask, "gold_fidelity_blocker"] = False
        guarded.loc[inference_mask, "identity_risk"] = False
        guarded.loc[inference_mask, "identity_risk_reasons"] = "alignment_context_gap"
        guarded.loc[inference_mask, "high_value_identity_risk"] = False
        guarded.loc[inference_mask, "alignment_context_gap"] = True
    if "alignment_context_gap" not in guarded.columns:
        guarded["alignment_context_gap"] = False
    guarded["alignment_context_gap"] = guarded["alignment_context_gap"].where(guarded["alignment_context_gap"].notna(), False).astype(bool)
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

    ocr_evidence_payload, ocr_evidence_rows, ocr_evidence_fragments = _build_ocr_evidence_report(detail, character_reocr_debug)
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
        "core_identity_summary": core_identity_summary.to_dict(orient="records"),
        "script_limited_policy_summary": script_limited_policy_summary.to_dict(orient="records"),
        "script_limited_policy_rows": script_limited_policy_detail.to_dict(orient="records"),
        "latin_residual_policy_summary": latin_residual_policy_summary.to_dict(orient="records"),
        "latin_residual_policy_rows": latin_residual_policy_detail.to_dict(orient="records"),
        "core_identity_verified_rows": core_identity_detail.to_dict(orient="records"),
        "alignment_guard_summary": alignment_guard_summary.to_dict(orient="records"),
        "alignment_context_gaps": alignment_context_gaps.to_dict(orient="records"),
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
        "ocr_evidence_summary": ocr_evidence_payload.get("summary", {}),
        "ocr_evidence_status_summary": ocr_evidence_payload.get("status_summary", []),
        "ocr_evidence_rows": ocr_evidence_rows.to_dict(orient="records"),
        "ocr_evidence_fragments": ocr_evidence_fragments.to_dict(orient="records"),
        "details": detail.to_dict(orient="records"),
    }
    json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    reocr_debug_json_path = output_dir / "character_reocr_debug_report.json"
    reocr_debug_json_path.write_text(json.dumps({"summary": character_reocr_debug_summary.to_dict(orient="records"), "details": character_reocr_debug.to_dict(orient="records")}, ensure_ascii=False, indent=2), encoding="utf-8")
    ocr_evidence_json_path = output_dir / "ocr_evidence_report.json"
    ocr_evidence_json_path.write_text(json.dumps(_json_safe(ocr_evidence_payload), ensure_ascii=False, indent=2), encoding="utf-8")
    gold_core_json_path = output_dir / "gold_core_blocker_report.json"
    gold_core_json_path.write_text(json.dumps(_json_safe({"summary": gold_core_blocker_summary.to_dict(orient="records"), "details": gold_core_blocker_report.to_dict(orient="records")}), ensure_ascii=False, indent=2), encoding="utf-8")
    gold_core_resolution_json_path = output_dir / "gold_core_resolution_plan_report.json"
    gold_core_resolution_json_path.write_text(json.dumps(_json_safe({"summary": gold_core_resolution_summary.to_dict(orient="records"), "details": gold_core_resolution_plan.to_dict(orient="records")}), ensure_ascii=False, indent=2), encoding="utf-8")

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
        _sanitize_frame(core_identity_summary).to_excel(writer, sheet_name="core_identity", index=False)
        _sanitize_frame(core_identity_detail).to_excel(writer, sheet_name="core_identity_rows", index=False)
        _sanitize_frame(script_limited_policy_summary).to_excel(writer, sheet_name="script_policy", index=False)
        _sanitize_frame(script_limited_policy_detail).to_excel(writer, sheet_name="script_policy_rows", index=False)
        _sanitize_frame(latin_residual_policy_summary).to_excel(writer, sheet_name="latin_residual_policy", index=False)
        _sanitize_frame(latin_residual_policy_detail).to_excel(writer, sheet_name="latin_residual_rows", index=False)
        _sanitize_frame(alignment_guard_summary).to_excel(writer, sheet_name="alignment_guard", index=False)
        _sanitize_frame(alignment_context_gaps).to_excel(writer, sheet_name="alignment_context_gaps", index=False)
        _sanitize_frame(character_reocr_debug_summary).to_excel(writer, sheet_name="reocr_debug_summary", index=False)
        _sanitize_frame(character_reocr_debug).to_excel(writer, sheet_name="reocr_debug", index=False)
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

    ocr_evidence_xlsx_path = output_dir / "ocr_evidence_report.xlsx"
    with pd.ExcelWriter(ocr_evidence_xlsx_path, engine="openpyxl") as writer:
        _sanitize_frame(pd.DataFrame([ocr_evidence_payload.get("summary", {})])).to_excel(writer, sheet_name="summary", index=False)
        _sanitize_frame(pd.DataFrame(ocr_evidence_payload.get("status_summary", []))).to_excel(writer, sheet_name="status_summary", index=False)
        _sanitize_frame(ocr_evidence_rows).to_excel(writer, sheet_name="rows", index=False)
        _sanitize_frame(ocr_evidence_fragments).to_excel(writer, sheet_name="fragments", index=False)

    gold_core_resolution_xlsx_path = output_dir / "gold_core_resolution_plan_report.xlsx"
    with pd.ExcelWriter(gold_core_resolution_xlsx_path, engine="openpyxl") as writer:
        _sanitize_frame(gold_core_resolution_summary).to_excel(writer, sheet_name="summary", index=False)
        _sanitize_frame(gold_core_resolution_plan).to_excel(writer, sheet_name="details", index=False)

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
    print(f"OCR Evidence JSON:  {ocr_evidence_json_path}")
    print(f"OCR Evidence Excel: {ocr_evidence_xlsx_path}")
    print(f"Gold Core Resolution Plan JSON:  {gold_core_resolution_json_path}")
    print(f"Gold Core Resolution Plan Excel: {gold_core_resolution_xlsx_path}")
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
