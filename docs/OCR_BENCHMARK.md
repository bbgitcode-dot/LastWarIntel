# OCR Benchmark Framework

Version: v0.9.5

The OCR Benchmark Framework compares OCR providers on Sentinel's real Last War screenshots.

## Goal

Do not guess which OCR is better.

Measure it.

## Usage

Run the default benchmark:

```bash
python benchmark_ocr.py
```

Run only one provider:

```bash
python benchmark_ocr.py --providers easy
python benchmark_ocr.py --providers paddle
```

## Input

```text
/screenshots
```

## Output

```text
/output/easy_lastwar_export.xlsx
/output/paddle_lastwar_export.xlsx
/benchmarks/ocr_benchmark_report.xlsx
/benchmarks/ocr_benchmark_report.json
/benchmarks/easy_run.log
/benchmarks/paddle_run.log
```

## Metrics

The report includes:

- runtime
- sheet count
- total rows
- THP rows
- alliance rows
- server review rows
- UNKNOWN player names
- REVIEW rows
- VALID rows
- rank warnings
- server warnings
- benchmark score

## Score

The score is a transparent decision aid, not a hidden model.

Weighted categories:

- Server quality
- Rank integrity
- UNKNOWN reduction
- REVIEW reduction
- Row volume
- Runtime

## Decision Rule

The winning OCR provider is the one that produces the most reliable, actionable data for Sentinel's Last War screenshots.

Not the newest.

Not the fastest.

The best for this use case.
