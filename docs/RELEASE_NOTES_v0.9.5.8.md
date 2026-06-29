# Sentinel v0.9.5.8 - Ground Truth Validator Duplicate Column Hotfix

## Fixed

- Ground Truth Validator no longer crashes when OCR Excel exports contain duplicate `ocr_name` columns.
- Duplicate Excel columns are collapsed before validation.
- Scalar normalization now tolerates pandas Series/DataFrame values defensively.
- Validator can now compare Server 551 Ground Truth against the OCR export successfully.

## Verification

Command tested:

```bash
python ground_truth_validator.py --ground-truth input/S6_preTransfer_server_551_top50_THP.xlsx --ocr-output output/easy_lastwar_export.xlsx
```

Result on provided Server 551 dataset:

- Ground Truth rows: 50
- Matched rows: 44
- Missing rows: 6
- Name exact matches: 2
- Average name similarity: 0.2953
- Alliance matches: 12
- Power matches: 13
- Rank matches: 34
- Usable identity matches: 4
- Score: 34.13
