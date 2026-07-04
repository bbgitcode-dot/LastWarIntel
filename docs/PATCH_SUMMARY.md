# Patch Summary – v0.9.5.100

## Sentinel v0.9.5.100 – Ground Truth Alignment Guard

This sprint fixes the validator-level false comparison pattern found after v0.9.5.99. Contextual inference rows are useful for explaining bounded gaps, but they are not safe row-level OCR matches and must not generate character-level diffs.

## Key changes

- Added `_apply_alignment_guard()` in `ground_truth_validator.py`.
- Suppressed Character Verification / ReOCR for `inference_context_gap` rows.
- Added `alignment_context_gap`, `alignment_guard_status`, and `alignment_safe_for_character_verification` detail fields.
- Added report sections/sheets for Alignment Guard diagnostics.
- Added regression test `tests/smoke/test_alignment_guard_100.py`.

## Validation

```bash
pytest -q tests/smoke/test_alignment_guard_100.py
python -m py_compile ground_truth_validator.py inference/context_engine.py parser/targeted_character_reocr.py
```

## Version

`0.9.5.100`
