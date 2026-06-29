"""Benchmark OCR providers against Sentinel's real screenshot pipeline.

This tool intentionally keeps parser, quality gates and Excel export identical.
The only changed variable is the OCR provider selected through
``SENTINEL_OCR_PROVIDER``.

Usage:
    python benchmark_ocr.py
    python benchmark_ocr.py --providers easy,paddle
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_PROVIDERS = ("easy", "paddle")
OUTPUT_DIR = Path("output")
BENCHMARK_DIR = Path("benchmarks")


@dataclass(slots=True)
class ProviderBenchmarkResult:
    provider: str
    status: str
    runtime_seconds: float
    output_file: str
    sheets: int = 0
    rows: int = 0
    thp_rows: int = 0
    alliance_rows: int = 0
    server_review_rows: int = 0
    unknown_names: int = 0
    review_rows: int = 0
    valid_rows: int = 0
    rank_warnings: int = 0
    server_warnings: int = 0
    error: str | None = None


def _provider_output_file(provider: str) -> Path:
    return OUTPUT_DIR / f"{provider}_lastwar_export.xlsx"


def _provider_log_file(provider: str) -> Path:
    return BENCHMARK_DIR / f"{provider}_run.log"


def _run_provider(provider: str) -> ProviderBenchmarkResult:
    OUTPUT_DIR.mkdir(exist_ok=True)
    BENCHMARK_DIR.mkdir(exist_ok=True)

    output_file = _provider_output_file(provider)
    log_file = _provider_log_file(provider)
    if output_file.exists():
        output_file.unlink()

    env = os.environ.copy()
    env["SENTINEL_OCR_PROVIDER"] = provider
    env["SENTINEL_OUTPUT_FILE"] = str(output_file)

    start = time.perf_counter()
    completed = subprocess.run(
        [sys.executable, "main.py"],
        cwd=Path.cwd(),
        env=env,
        capture_output=True,
        text=True,
    )
    runtime = time.perf_counter() - start
    log_file.write_text(
        "STDOUT\n======\n" + completed.stdout + "\n\nSTDERR\n======\n" + completed.stderr,
        encoding="utf-8",
    )

    if completed.returncode != 0:
        return ProviderBenchmarkResult(
            provider=provider,
            status="ERROR",
            runtime_seconds=round(runtime, 3),
            output_file=str(output_file),
            error=(completed.stderr or completed.stdout)[-4000:],
        )

    result = ProviderBenchmarkResult(
        provider=provider,
        status="OK",
        runtime_seconds=round(runtime, 3),
        output_file=str(output_file),
    )
    if output_file.exists():
        _collect_excel_metrics(output_file, result)
    else:
        result.status = "ERROR"
        result.error = "Provider run completed but no Excel output was created."
    return result


def _count_contains(series: pd.Series, text: str) -> int:
    return int(series.fillna("").astype(str).str.contains(text, case=False, regex=False).sum())


def _collect_excel_metrics(path: Path, result: ProviderBenchmarkResult) -> None:
    book = pd.read_excel(path, sheet_name=None)
    result.sheets = len(book)

    for sheet_name, df in book.items():
        rows = len(df)
        result.rows += rows
        lowered = sheet_name.lower()

        if "total_hero_power" in lowered:
            result.thp_rows += rows
            if "player_name" in df.columns:
                result.unknown_names += int((df["player_name"].fillna("").astype(str) == "UNKNOWN").sum())
            if "parse_status" in df.columns:
                status = df["parse_status"].fillna("").astype(str)
                result.review_rows += int((status == "REVIEW").sum())
                result.valid_rows += int((status == "VALID").sum())
            if "rank_warning" in df.columns:
                result.rank_warnings += int(df["rank_warning"].fillna("").astype(str).ne("").sum())
            if "server_warning" in df.columns:
                result.server_warnings += int(df["server_warning"].fillna("").astype(str).ne("").sum())
        elif "alliance_power" in lowered:
            result.alliance_rows += rows
            if "rank_warning" in df.columns:
                result.rank_warnings += int(df["rank_warning"].fillna("").astype(str).ne("").sum())
            if "server_warning" in df.columns:
                result.server_warnings += int(df["server_warning"].fillna("").astype(str).ne("").sum())
        elif "server_review" in lowered:
            result.server_review_rows += rows


def _score(result: ProviderBenchmarkResult, all_results: list[ProviderBenchmarkResult]) -> float:
    """Return a coarse benchmark score. Higher is better.

    The score is intentionally transparent. It is not a scientific truth; it is
    a repeatable decision aid for comparing OCR providers on Sentinel data.
    """
    if result.status != "OK":
        return 0.0

    max_runtime = max((r.runtime_seconds for r in all_results if r.status == "OK"), default=result.runtime_seconds)
    runtime_score = 1.0 if max_runtime <= 0 else max(0.0, 1.0 - (result.runtime_seconds / max_runtime) * 0.5)

    thp = max(result.thp_rows, 1)
    unknown_score = max(0.0, 1.0 - result.unknown_names / thp)
    review_score = max(0.0, 1.0 - result.review_rows / thp)
    rank_score = max(0.0, 1.0 - result.rank_warnings / max(result.rows, 1))
    server_score = max(0.0, 1.0 - result.server_review_rows / max(result.sheets, 1))
    volume_score = min(1.0, result.rows / max((r.rows for r in all_results if r.status == "OK"), default=max(result.rows, 1)))

    weighted = (
        server_score * 0.25
        + rank_score * 0.20
        + unknown_score * 0.20
        + review_score * 0.15
        + volume_score * 0.10
        + runtime_score * 0.10
    )
    return round(weighted * 100, 2)



ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
ILLEGAL_EXCEL_CHARS_RE = re.compile(r"[\x00-\x08\x0b-\x0c\x0e-\x1f]")


def _sanitize_cell(value: Any) -> Any:
    if isinstance(value, str):
        value = ANSI_ESCAPE_RE.sub("", value)
        value = ILLEGAL_EXCEL_CHARS_RE.sub("", value)
        return value
    return value


def _sanitize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{key: _sanitize_cell(value) for key, value in row.items()} for row in rows]

def _write_reports(results: list[ProviderBenchmarkResult]) -> None:
    BENCHMARK_DIR.mkdir(exist_ok=True)

    rows: list[dict[str, Any]] = []
    for result in results:
        row = asdict(result)
        row["score"] = _score(result, results)
        rows.append(row)

    safe_rows = _sanitize_rows(rows)

    json_path = BENCHMARK_DIR / "ocr_benchmark_report.json"
    json_path.write_text(json.dumps(safe_rows, ensure_ascii=False, indent=2), encoding="utf-8")

    xlsx_path = BENCHMARK_DIR / "ocr_benchmark_report.xlsx"
    df = pd.DataFrame(safe_rows)
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="summary", index=False)

    print("\n===== OCR BENCHMARK SUMMARY =====")
    print(df[["provider", "status", "score", "runtime_seconds", "rows", "unknown_names", "review_rows", "rank_warnings", "server_review_rows"]].to_string(index=False))
    print(f"\nBenchmark JSON: {json_path}")
    print(f"Benchmark Excel: {xlsx_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark OCR providers for Sentinel.")
    parser.add_argument(
        "--providers",
        default=",".join(DEFAULT_PROVIDERS),
        help="Comma-separated provider list. Supported: easy,paddle",
    )
    args = parser.parse_args()

    providers = [provider.strip().lower() for provider in args.providers.split(",") if provider.strip()]
    results = [_run_provider(provider) for provider in providers]
    _write_reports(results)


if __name__ == "__main__":
    main()
