## v0.9.5.117 – Reconstruction Candidate Gate

Built from v0.9.5.116. The key change is a conservative gate around Latin Name Block Reconstruction. Do not broaden this path unless the run evidence shows it preserves DATAGUARD and improves core identity. For the next sprint, inspect runtime_debug_report.json and character_reocr_debug_report.json to confirm how many block reconstructions were avoided and whether core identity stayed stable.

# Handoff Next Chat – Sentinel v0.9.5.102

Use `Sentinel_v0.9.5.102.zip` as the next baseline.

## Current focus

Sentinel is in the 551 Gold Fidelity phase. DataGuard and Alignment Guard are working: unsafe context gaps are not treated as character drift and Operational Truth remains protected.

The current blocker is Character ReOCR effectiveness. v0.9.5.101 produced the same practical result as the prior run, so v0.9.5.102 adds instrumentation instead of guessing another crop change.

## What v0.9.5.102 adds

The Ground Truth Validator now emits:

```text
benchmarks/character_reocr_debug_report.json
benchmarks/character_reocr_debug_report.xlsx
```

These reports flatten every Character ReOCR target and show:

- rank and OCR rank;
- expected and OCR identity;
- screenshot name and row slot;
- crop box and crop strategy;
- target field / position / expected / observed;
- OCR vote variants and raw vote text;
- selected glyph, confidence and final target status.

## Next validation request

Run the validator again on the existing 551 export:

```bash
python ground_truth_validator.py --ocr-output output\snapshots\s6-pre-transfer-2b69ebc1\lastwar_export.xlsx
```

Then inspect/post:

```text
benchmarks/character_reocr_debug_report.xlsx
benchmarks/character_reocr_debug_report.json
```

## Next likely sprint

v0.9.5.103 should be chosen after reviewing the debug report. Likely options:

1. Row-slot correction if crops are pointed at the wrong row.
2. Field geometry correction if crops are systematically shifted left/right.
3. Vote extraction correction if OCR sees the right text but Sentinel selects the wrong glyph.
4. OCR-provider strategy if crops are correct but EasyOCR cannot read the target glyphs.

Do not start Entity Intelligence yet. Data Quality comes first.

## v0.9.5.103 Update – ReOCR Row Slot & Field Anchor Correction

The v0.9.5.102 debug reports proved that Character ReOCR failures are mostly localization failures, not raw OCR failures. v0.9.5.103 therefore adds 551-window screenshot row geometry and explicit crop-anchor diagnostics so future runs can separate wrong-row/wrong-field crops from true character-recognition misses. Operational Truth remains unchanged; ReOCR remains evidence-only.

## v0.9.5.116 – Latin Name Block Reconstruction

- Added screenshot-local Latin Name Block Reconstruction for aligned Latin-only player names where single-glyph ReOCR is too weak, e.g. missing/shifted characters such as `Mizzenmast -> Mzzenmast`, `Drpeek -> Ieek`, and spacing/digit drifts like `N E R D -> NER0`.
- Reconstruction is DATAGUARD-gated: it only runs on accepted/aligned rows, does not use historical identity data, and refuses mixed CJK/Hangul/Kana display drift.
- Added reconstruction evidence to the existing character ReOCR debug stream with crop strategy `latin_name_block`, candidate text, selected reconstruction, confidence, and timing.
- Core Identity can now accept a verified Latin name block when the whole-name OCR candidate supports the expected display more strongly than the observed OCR string.

## Handoff v0.9.5.118

Use `Sentinel_v0.9.5.118.zip` as the next baseline. The patch introduces script-limited core identity metrics for mixed Latin/CJK/Hangul names. After the next run, compare `script_limited_core_identity_matches`, `verified_core_identity_matches`, and `gold_core_blocker_rows` against `.117`. Full Display Gold should remain conservative.

