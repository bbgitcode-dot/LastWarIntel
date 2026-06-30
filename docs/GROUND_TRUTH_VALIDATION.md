# Ground Truth Validation

Sentinel's OCR output must be measurable against manually verified data.
The Ground Truth Validator compares a curated THP sheet with a normal Sentinel
OCR export and produces accuracy metrics for names, alliances, power and rank.

## Input

Ground truth workbook columns:

```text
Server | Rank | Alliance | HeroPower | TrueName | Screenshot
```

Example:

```text
551 | 2 | IVE | 320306014 | MEITTü メ 메잇 | 2026-06-29 14_45_10-Window.png
```

## Run

```bash
python ground_truth_validator.py ^
  --ground-truth input/S6_preTransfer_server_551_top50_THP.xlsx ^
  --ocr-output output/easy_lastwar_export.xlsx
```

## Output

```text
benchmarks/ground_truth_validation_report.xlsx
benchmarks/ground_truth_validation_report.json
```

The report contains:

- overall score
- exact name accuracy
- average name similarity
- alliance accuracy
- power accuracy
- rank accuracy
- usable identity matches
- category breakdown for Latin, mixed CJK, Hangul, Kana and Han names
- failure rows for manual inspection

## Why this exists

OCR accuracy must not be guessed. Sentinel uses ground truth data to verify
whether OCR output is reliable enough for Player Identity and Player Mobility.

Reliable Intelligence begins with reliable data.

## v0.9.5.26 operational workflow

After a normal import run, the validator can be executed with default paths:

```bash
python ground_truth_validator.py
```

Default inputs:

```text
ground_truth/S6/server_551/top50_THP.xlsx
output/lastwar_export.xlsx
```

The validator now scopes precision to the Ground Truth server. In a multi-server export, Server 549 and Server 550 THP rows no longer dilute the Server 551 Top 50 precision metric.

The report also reads `REVIEW_ranking_guard_quarantine` when present. This allows Sentinel to distinguish between:

- a Ground Truth player correctly exported,
- a tempting but blocked rank fallback,
- a truly missing row,
- and a row protected by the Ranking Guard quarantine.

New report fields include:

- `validation_server`
- `ocr_scope_rows`
- `ocr_total_rows`
- `quarantine_rows`
- `quarantine_scope_rows`
- `ground_truth_quarantined_rows`
- `export_extra_rows`
- `failure_class` per detail row
- `failure_summary` in JSON and Excel output

This turns Ground Truth validation from a historical benchmark into a transfer-phase quality gate.
