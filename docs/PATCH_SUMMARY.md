# Patch Summary – v0.9.5.101

## Sentinel v0.9.5.101 – Character Crop Precision Guard

This sprint addresses the post-v0.9.5.100 finding that Character ReOCR activated correctly but confirmed too few expected glyphs. The issue was not only OCR quality; the crop/vote layer was polluted by neighbouring UI text.

## Key changes

- Refined player-name crop geometry to begin after the alliance tag.
- Added position-aware alliance-tag vote extraction for bracketed tags.
- Restricted accepted vote characters to expected/observed/confusion-family glyphs.
- Off-target OCR output now resolves to `unresolved` instead of becoming misleading evidence.
- Added smoke regressions for tag-position voting and noise rejection.

## Validation

```bash
pytest -q tests/smoke/test_targeted_character_reocr_97.py tests/smoke/test_character_reocr_98.py tests/smoke/test_alignment_guard_100.py
python -m py_compile ground_truth_validator.py parser/targeted_character_reocr.py
```

## Version

`0.9.5.101`
