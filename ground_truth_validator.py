"""Validate Sentinel OCR output against manually curated ground truth.

The validator compares a Ground Truth Excel file with a Sentinel OCR export.
It is intentionally independent from OCR providers: it measures the result that
actually matters for later Player Mobility and Identity Matching.

Usage:
    python ground_truth_validator.py \
        --ground-truth input/S6_preTransfer_server_551_top50_THP.xlsx \
        --ocr-output output/easy_lastwar_export.xlsx

Outputs:
    benchmarks/ground_truth_validation_report.xlsx
    benchmarks/ground_truth_validation_report.json
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_OUTPUT_DIR = Path("benchmarks")

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
ILLEGAL_EXCEL_CHARS_RE = re.compile(r"[\x00-\x08\x0b-\x0c\x0e-\x1f]")
TAG_RE = re.compile(r"^\s*\[\s*([A-Za-z0-9]{2,6})\s*\]\s*(.*)$")

# Unicode ranges useful for high-level reporting. The validator does not need
# to know the user's language; these tags help us measure where OCR struggles.
HAN_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
KANA_RE = re.compile(r"[\u3040-\u30ff]")
HANGUL_RE = re.compile(r"[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]")
LATIN_RE = re.compile(r"[A-Za-z]")


@dataclass(slots=True)
class ValidationSummary:
    ground_truth_rows: int
    matched_rows: int
    missing_rows: int
    name_exact_matches: int
    name_similarity_avg: float
    alliance_matches: int
    power_matches: int
    rank_matches: int
    usable_identity_matches: int
    score: float


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
    ocr["server"] = ocr["server"].map(safe_int)
    ocr["rank"] = ocr["rank"].map(safe_int)
    ocr["power"] = ocr["power"].map(safe_int)
    ocr["alliance"] = ocr["alliance"].map(normalize_tag)
    ocr["ocr_name"] = ocr["ocr_name"].map(normalize_name)
    if "source_file" not in ocr.columns:
        ocr["source_file"] = ""
    return ocr


def _similarity(expected: str, actual: str) -> float:
    expected_n = normalize_name(expected).casefold()
    actual_n = normalize_name(actual).casefold()
    if not expected_n and not actual_n:
        return 1.0
    if not expected_n or not actual_n:
        return 0.0
    return SequenceMatcher(None, expected_n, actual_n).ratio()


def _find_match(gt_row: pd.Series, ocr: pd.DataFrame) -> tuple[pd.Series | None, str]:
    server = gt_row["server"]
    rank = gt_row["rank"]
    power = gt_row["power"]

    candidates = ocr[ocr["server"] == server]
    by_rank = candidates[candidates["rank"] == rank]
    if not by_rank.empty:
        return by_rank.iloc[0], "server_rank"

    by_power = candidates[candidates["power"] == power]
    if not by_power.empty:
        return by_power.iloc[0], "server_power"

    # Last resort: very small power tolerance for values that were normalized
    # slightly differently. THP is expected to be exact, so this remains strict.
    if power:
        tolerance = max(1, int(power * 0.00001))
        by_near_power = candidates[(candidates["power"] - power).abs() <= tolerance]
        if not by_near_power.empty:
            return by_near_power.iloc[0], "server_near_power"

    return None, "missing"


def validate(ground_truth: pd.DataFrame, ocr: pd.DataFrame) -> tuple[ValidationSummary, pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    for _, gt_row in ground_truth.iterrows():
        match, match_method = _find_match(gt_row, ocr)
        expected_name = normalize_name(gt_row["true_name"])
        expected_alliance = normalize_tag(gt_row["alliance"])
        expected_power = safe_int(gt_row["power"])
        expected_rank = safe_int(gt_row["rank"])

        if match is None:
            actual_name = ""
            actual_alliance = ""
            actual_power = None
            actual_rank = None
            source_file = ""
            ocr_sheet = ""
        else:
            actual_name = normalize_name(match.get("ocr_name", ""))
            actual_alliance = normalize_tag(match.get("alliance", ""))
            actual_power = safe_int(match.get("power"))
            actual_rank = safe_int(match.get("rank"))
            source_file = normalize_text(match.get("source_file", ""))
            ocr_sheet = normalize_text(match.get("ocr_sheet", ""))

        name_similarity = _similarity(expected_name, actual_name)
        name_exact = normalize_name(expected_name).casefold() == normalize_name(actual_name).casefold()
        alliance_match = expected_alliance == actual_alliance
        power_match = expected_power == actual_power
        rank_match = expected_rank == actual_rank
        usable_identity = bool(match is not None and power_match and alliance_match and name_similarity >= 0.80)

        rows.append({
            "server": gt_row["server"],
            "rank": expected_rank,
            "expected_alliance": expected_alliance,
            "ocr_alliance": actual_alliance,
            "alliance_match": alliance_match,
            "expected_power": expected_power,
            "ocr_power": actual_power,
            "power_match": power_match,
            "expected_name": expected_name,
            "ocr_name": actual_name,
            "name_exact_match": name_exact,
            "name_similarity": round(name_similarity, 4),
            "usable_identity_match": usable_identity,
            "name_category": gt_row["name_category"],
            "match_method": match_method,
            "rank_match": rank_match,
            "ocr_rank": actual_rank,
            "ground_truth_screenshot": normalize_text(gt_row.get("screenshot", "")),
            "ocr_source_file": source_file,
            "ocr_sheet": ocr_sheet,
        })

    detail = pd.DataFrame(rows)
    total = len(detail)
    matched = int((detail["match_method"] != "missing").sum())
    name_exact = int(detail["name_exact_match"].sum())
    alliance_matches = int(detail["alliance_match"].sum())
    power_matches = int(detail["power_match"].sum())
    rank_matches = int(detail["rank_match"].sum())
    usable_matches = int(detail["usable_identity_match"].sum())
    avg_similarity = round(float(detail["name_similarity"].mean()) if total else 0.0, 4)

    # Score weights direct identity needs: power/rank/alliance establish row,
    # name quality establishes reusable Player Identity.
    score = round((
        (matched / max(total, 1)) * 0.15
        + (power_matches / max(total, 1)) * 0.15
        + (rank_matches / max(total, 1)) * 0.10
        + (alliance_matches / max(total, 1)) * 0.20
        + (name_exact / max(total, 1)) * 0.25
        + avg_similarity * 0.15
    ) * 100, 2)

    summary = ValidationSummary(
        ground_truth_rows=total,
        matched_rows=matched,
        missing_rows=total - matched,
        name_exact_matches=name_exact,
        name_similarity_avg=avg_similarity,
        alliance_matches=alliance_matches,
        power_matches=power_matches,
        rank_matches=rank_matches,
        usable_identity_matches=usable_matches,
        score=score,
    )

    category = detail.groupby("name_category", dropna=False).agg(
        rows=("rank", "count"),
        matched_rows=("match_method", lambda s: int((s != "missing").sum())),
        name_exact_matches=("name_exact_match", "sum"),
        avg_name_similarity=("name_similarity", "mean"),
        alliance_matches=("alliance_match", "sum"),
        power_matches=("power_match", "sum"),
        usable_identity_matches=("usable_identity_match", "sum"),
    ).reset_index()
    category["avg_name_similarity"] = category["avg_name_similarity"].round(4)

    return summary, detail, category


def _sanitize_cell(value: Any) -> Any:
    if isinstance(value, str):
        return ILLEGAL_EXCEL_CHARS_RE.sub("", ANSI_ESCAPE_RE.sub("", value))
    return value


def _sanitize_frame(df: pd.DataFrame) -> pd.DataFrame:
    return df.map(_sanitize_cell)


def write_report(summary: ValidationSummary, detail: pd.DataFrame, category: pd.DataFrame, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_rows = [asdict(summary)]
    failures = detail[
        (detail["match_method"] == "missing")
        | (~detail["name_exact_match"])
        | (~detail["alliance_match"])
        | (~detail["power_match"])
    ].copy()

    json_path = output_dir / "ground_truth_validation_report.json"
    json_payload = {
        "summary": summary_rows[0],
        "category_summary": category.to_dict(orient="records"),
        "details": detail.to_dict(orient="records"),
    }
    json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    xlsx_path = output_dir / "ground_truth_validation_report.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        pd.DataFrame(summary_rows).to_excel(writer, sheet_name="summary", index=False)
        _sanitize_frame(category).to_excel(writer, sheet_name="category_summary", index=False)
        _sanitize_frame(detail).to_excel(writer, sheet_name="details", index=False)
        _sanitize_frame(failures).to_excel(writer, sheet_name="failures", index=False)

    print("\n===== GROUND TRUTH VALIDATION SUMMARY =====")
    print(pd.DataFrame(summary_rows).to_string(index=False))
    print("\nCategory summary:")
    print(category.to_string(index=False))
    print(f"\nReport JSON:  {json_path}")
    print(f"Report Excel: {xlsx_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Sentinel OCR output against a Ground Truth Excel file.")
    parser.add_argument("--ground-truth", required=True, help="Path to manually curated ground truth Excel file.")
    parser.add_argument("--ocr-output", default="output/easy_lastwar_export.xlsx", help="Path to Sentinel OCR export Excel file.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for validation reports.")
    args = parser.parse_args()

    ground_truth_path = Path(args.ground_truth)
    ocr_output_path = Path(args.ocr_output)
    output_dir = Path(args.output_dir)

    gt = load_ground_truth(ground_truth_path)
    ocr = load_ocr_output(ocr_output_path)
    summary, detail, category = validate(gt, ocr)
    write_report(summary, detail, category, output_dir)


if __name__ == "__main__":
    main()
