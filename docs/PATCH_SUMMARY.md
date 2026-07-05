# Patch Summary – v0.9.5.102

## Sentinel v0.9.5.102 – Character ReOCR Debug Instrumentation

v0.9.5.102 is a diagnostic Gold Fidelity sprint. v0.9.5.101 did not improve the 551 validation result enough, which means continuing to tune crop geometry blindly would risk wasting time. This sprint makes the Character ReOCR path inspectable.

## What changed

- Added `character_reocr_debug_report.json`.
- Added `character_reocr_debug_report.xlsx`.
- Added flattened per-target ReOCR diagnostics:
  - server / rank / OCR rank;
  - expected vs OCR name and alliance tag;
  - screenshot and row slot;
  - crop box, crop width, crop height and crop strategy;
  - target field, position, expected glyph and observed glyph;
  - vote variants, vote texts, selected glyph, confidence and status.
- Extended `CharacterVerificationEvidence` with diagnostic metadata:
  - `crop_strategy`;
  - `text_length`;
  - `expected_text`;
  - `observed_text`;
  - `allowed_chars`.
- Kept Operational Truth immutable. The new data is evidence only.

## Why this matters

The previous run showed:

```text
character_reocr_target_count = 183
character_reocr_verified_expected = 18
character_reocr_verified_observed = 11
character_reocr_unresolved = 150
```

The critical question is no longer whether ReOCR is invoked. It is why expected-verifiable targets remain unresolved. v0.9.5.102 answers that by exposing whether the problem is row-slot alignment, crop geometry, OCR provider output, or vote selection.

## Validation

```bash
pytest -q tests/smoke/test_character_reocr_debug_102.py tests/smoke/test_targeted_character_reocr_97.py tests/smoke/test_character_reocr_98.py tests/smoke/test_alignment_guard_100.py
python -m py_compile ground_truth_validator.py parser/targeted_character_reocr.py
```

## Version

`0.9.5.102`
