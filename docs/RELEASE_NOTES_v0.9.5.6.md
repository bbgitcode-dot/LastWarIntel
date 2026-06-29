# Sentinel v0.9.5.6 - Ground Truth Validation Framework

## Added

- `ground_truth_validator.py`
- Ground Truth Excel comparison
- Name accuracy metrics
- Alliance accuracy metrics
- Power and rank accuracy metrics
- Usable identity match metric
- Name category breakdown for Latin/CJK/mixed names
- JSON and Excel validation reports
- Documentation: `docs/GROUND_TRUTH_VALIDATION.md`

## Purpose

This release adds the first objective OCR quality measurement against manually
curated truth data. It allows Sentinel to measure whether OCR output is good
enough for Player Identity and later Player Mobility.

## Run

```bash
python ground_truth_validator.py --ground-truth input/S6_preTransfer_server_551_top50_THP.xlsx --ocr-output output/easy_lastwar_export.xlsx
```

The Sentinel approves.
