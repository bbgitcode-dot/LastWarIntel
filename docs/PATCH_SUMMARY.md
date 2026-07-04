# Patch Summary – v0.9.5.99

## Sentinel v0.9.5.99 – Character Re-OCR Provider Input Fix

Fixes the `.98` crash in `ground_truth_validator.py`: targeted character re-OCR now converts PIL variant crops to numpy arrays before invoking EasyOCR. This keeps the standard validator command usable while preserving the no-auto-canonicalization rule.

## Validation

```text
py_compile OK
targeted fake-reader smoke OK
zip integrity OK
```

## Version

`0.9.5.99`
