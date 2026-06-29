# Sentinel v0.9.5.7 – Ground Truth Validator Import Hotfix

## Fixed

- Ground Truth Validator no longer requires an explicit `server` column in OCR exports.
- Server is derived from THP sheet names such as `551_total_hero_power` when missing.
- Duplicate OCR name columns are collapsed safely.
- OCR exports with `ocr_name`, `player_name`, or `name` variants are handled robustly.
- Alliance/tag aliases are normalized before validation.

## Command

```bash
python ground_truth_validator.py --ground-truth input/S6_preTransfer_server_551_top50_THP.xlsx --ocr-output output/easy_lastwar_export.xlsx
```
