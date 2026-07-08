# Patch Summary – v0.9.5.120 OCR Evidence Inspector and Row Integrity Diagnostics

## Purpose

v0.9.5.120 turns the recent Thunder/YUNS discussion into diagnostics. The goal is not to guess identities and not to add another OCR heuristic. The goal is to expose whether a suspicious name came from the correct row, whether ReOCR crops are leaking into neighbouring fields, and which visual evidence Sentinel actually used.

## Changes

- Adds an OCR Evidence Inspector report to the Ground Truth Validator.
- New report files:
  - `benchmarks/ocr_evidence_report.json`
  - `benchmarks/ocr_evidence_report.xlsx`
- Adds OCR evidence sections to the main Ground Truth JSON and Excel report.
- Adds row-level integrity statuses such as:
  - `ROW_OK_NO_REOCR`
  - `ROW_OK_WITH_REOCR`
  - `ROW_CONTEXT_GAP`
  - `ROW_FIELD_MISMATCH_DIAGNOSTIC`
  - `ROW_REOCR_UNRESOLVED`
  - `ROW_OBSERVED_TEXT_CONFIRMED`
- Preserves fragment provenance from Character ReOCR:
  - screenshot
  - row slot
  - crop box
  - target field
  - target position
  - selected glyph
  - crop strategy
  - crop anchor status
  - diagnostic text
  - vote texts
- Keeps Operational Truth unchanged.
- Keeps DataGuard, Ranking Guard, matching, inference, and ReOCR voting unchanged.

## Why

The remaining hard cases are no longer only OCR quality questions. Before Sentinel should resolve identity across snapshots, it must first prove that a parsed player name came from the correct visual row and field.

This patch adds the evidence layer needed to distinguish:

- bad OCR,
- bad crop geometry,
- bad row/field mapping,
- contextual gaps,
- script-limited display drift.

## Validation

```text
12 passed – OCR Evidence Inspector + recent identity policy regressions
py_compile OK
zip integrity OK
```

## Commit

```bash
git add .
git commit -m "feat(data-guard): add OCR evidence inspector diagnostics"
git tag -a v0.9.5.120 -m "v0.9.5.120 OCR Evidence Inspector and Row Integrity Diagnostics"
```
