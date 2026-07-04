# Handoff Next Chat – Sentinel v0.9.5.98

Use `Sentinel_v0.9.5.98.zip` as the next baseline.

## What changed

The Ground Truth validator now auto-activates targeted Character Re-OCR evidence when screenshots are available. `--screenshots-dir` can point to either a directory or a ZIP, including `551.zip`. If no OCR provider is available, targets are still emitted as unresolved instead of staying at zero.

## Recommended validation

```bash
python ground_truth_validator.py --ocr-output output\snapshots\s6-pre-transfer-2b69ebc1\lastwar_export.xlsx --screenshots-dir 551.zip
```

Expected important change versus v0.9.5.97:

```text
character_reocr_target_count > 0
```

Gold-ready is still expected to be false until targeted crop OCR starts verifying expected glyphs reliably.

## Next sprint recommendation

v0.9.5.99 should focus on crop geometry and voting quality for high-value Character Verification targets, not cache or broad performance.
