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
from parser.targeted_character_reocr import parse_reocr_targets, verify_target_from_screenshot, summarize_evidence, filter_local_glyph_targets
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
            skipped_targets = max(0, len(raw_targets) - len(local_targets))
            for target in local_targets:
                expected_text = expected_name if target.field == "player_name" else expected_alliance_display
                observed_text = actual_name if target.field == "player_name" else actual_alliance_display
                evidence_items.append(verify_target_from_screenshot(
                    screenshot_path=screenshot_path,
                    target=target,
                    expected_text=expected_text,
                    observed_text=observed_text,
                    row_slot=row_slot,
                    reader=character_reocr_reader,
                ))
            reocr_summary = summarize_evidence(evidence_items)
            reocr_summary["skipped_nonlocal"] = skipped_targets
            reocr_evidence_json = json.dumps([item.to_dict() for item in evidence_items], ensure_ascii=False)
            if reocr_summary["targets"] == 0:
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

        verified_name_display_exact = bool(accepted_match and _field_verified_by_reocr(
            already_exact=name_display_exact,
            raw_target_count=raw_player_targets,
            local_target_count=local_player_targets,
            skipped_target_count=skipped_player_targets,
            verified_expected_count=verified_player_expected,
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
        verified_exact_identity = bool(accepted_match and rank_match and power_match and verified_name_display_exact and verified_alliance_display_exact)
        verified_identity_resolution = bool(verified_exact_identity and not exact_identity)

        identity_risk_reasons = []
        if accepted_match and not verified_name_display_exact:
            identity_risk_reasons.append("player_name_display_drift")
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
            "verified_exact_identity_match": verified_exact_identity,
            "verified_identity_resolution": verified_identity_resolution,
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
    ).reset_index() if not identity_risk_detail.empty else pd.DataFrame(columns=["identity_risk_reasons", "rows", "high_value_rows", "usable_identity_matches", "exact_identity_matches", "verified_exact_identity_matches", "verified_identity_resolution_rows"])

    gold_fidelity_blockers = detail[detail.get("gold_fidelity_blocker", pd.Series(dtype=bool))].copy()
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
    ).reset_index() if not character_verification_detail.empty else pd.DataFrame(columns=["character_verification_reasons", "rows", "high_value_rows", "exact_identity_matches", "verified_exact_identity_matches", "verified_identity_resolution_rows"])
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

    json_payload = {
        "summary": summary_rows[0],
        "category_summary": category.to_dict(orient="records"),
        "failure_summary": failure_summary.to_dict(orient="records"),
        "identity_risk_summary": identity_risk_summary.to_dict(orient="records"),
        "identity_risks": identity_risk_detail.to_dict(orient="records"),
        "character_verification_summary": character_verification_summary.to_dict(orient="records"),
        "character_verification_candidates": character_verification_detail.to_dict(orient="records"),
        "gold_fidelity_blockers": gold_fidelity_blockers.to_dict(orient="records"),
        "alignment_guard_summary": alignment_guard_summary.to_dict(orient="records"),
        "alignment_context_gaps": alignment_context_gaps.to_dict(orient="records"),
        "character_reocr": {
            "target_count": int(detail.get("character_reocr_targets", pd.Series(dtype=int)).sum()),
            "verified_expected": int(detail.get("character_reocr_verified_expected", pd.Series(dtype=int)).sum()),
            "verified_display_resolutions": int(detail.get("verified_identity_resolution", pd.Series(dtype=bool)).sum()),
            "verified_observed": int(detail.get("character_reocr_verified_observed", pd.Series(dtype=int)).sum()),
            "unresolved": int(detail.get("character_reocr_unresolved", pd.Series(dtype=int)).sum()),
            "skipped_nonlocal": int(detail.get("character_reocr_skipped_nonlocal", pd.Series(dtype=int)).sum()),
            "debug_rows": int(len(character_reocr_debug)),
        },
        "character_reocr_debug_summary": character_reocr_debug_summary.to_dict(orient="records"),
        "character_reocr_debug": character_reocr_debug.to_dict(orient="records"),
        "details": detail.to_dict(orient="records"),
    }
    json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    reocr_debug_json_path = output_dir / "character_reocr_debug_report.json"
    reocr_debug_json_path.write_text(json.dumps({"summary": character_reocr_debug_summary.to_dict(orient="records"), "details": character_reocr_debug.to_dict(orient="records")}, ensure_ascii=False, indent=2), encoding="utf-8")

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
        _sanitize_frame(alignment_guard_summary).to_excel(writer, sheet_name="alignment_guard", index=False)
        _sanitize_frame(alignment_context_gaps).to_excel(writer, sheet_name="alignment_context_gaps", index=False)
        _sanitize_frame(character_reocr_debug_summary).to_excel(writer, sheet_name="reocr_debug_summary", index=False)
        _sanitize_frame(character_reocr_debug).to_excel(writer, sheet_name="reocr_debug", index=False)
        _sanitize_frame(detail).to_excel(writer, sheet_name="details", index=False)
        _sanitize_frame(failures).to_excel(writer, sheet_name="failures", index=False)

    reocr_debug_xlsx_path = output_dir / "character_reocr_debug_report.xlsx"
    with pd.ExcelWriter(reocr_debug_xlsx_path, engine="openpyxl") as writer:
        _sanitize_frame(character_reocr_debug_summary).to_excel(writer, sheet_name="summary", index=False)
        _sanitize_frame(character_reocr_debug).to_excel(writer, sheet_name="details", index=False)

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
