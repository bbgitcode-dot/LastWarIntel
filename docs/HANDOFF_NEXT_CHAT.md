# Handoff Next Chat – Sentinel v0.9.5.101

Use `Sentinel_v0.9.5.101.zip` as the next baseline.

## What changed

This sprint refines targeted Character ReOCR after v0.9.5.100 introduced the Alignment Guard. The key fix is evidence quality: player-name crops now start after the alliance tag, alliance-tag vote extraction is position-aware inside `[TAG]`, and off-target OCR noise is not accepted as ambiguous evidence.

## Recommended validation

```bash
python main.py
python ground_truth_validator.py --ocr-output output\snapshots\s6-pre-transfer-2b69ebc1\lastwar_export.xlsx
```

If screenshots are not auto-discovered in your local layout, pass the uploaded screenshot ZIP explicitly:

```bash
python ground_truth_validator.py --ocr-output output\snapshots\s6-pre-transfer-2b69ebc1\lastwar_export.xlsx --screenshots-dir 551.zip
```

## What to inspect

The decisive comparison versus v0.9.5.100 is whether cleaner crop/vote logic improves expected-glyph verification or at least removes misleading ambiguous votes:

```text
character_reocr_verified_expected
character_reocr_verified_observed
character_reocr_unresolved
character_reocr_evidence
```

## Next sprint recommendation

If expected confirmations are still low, the next sprint should add field-level OCR segmentation rather than further widening crops.
