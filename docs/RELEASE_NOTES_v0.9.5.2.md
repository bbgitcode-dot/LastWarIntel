# Sentinel v0.9.5.2 - OCR Provider Architecture Stabilization

## Fixed

- Stabilized the OCR provider architecture by replacing slotted dataclasses with plain provider classes.
- Fixed EasyOCR provider initialization error: `EasyOcrProvider object has no attribute 'profile'`.
- Fixed PaddleOCR provider initialization error: `PaddleOcrProvider object has no attribute '_metadata_language'`.
- Kept the provider interface unchanged so benchmark and main pipeline calls remain stable.

## Rationale

The OCR providers hold runtime state such as loaded readers, selected profiles and resolved language metadata. These values are created during initialization and should be normal instance attributes. The previous slotted dataclass implementation blocked attaching those attributes and caused both benchmark providers to fail before OCR could run.

## Validation

- Provider factory smoke tests pass.
- Benchmark metrics tests pass.
- Python compilation passes for OCR provider modules and benchmark runner.

## Git

```bash
git add .
git commit -m "fix(ocr): stabilize provider architecture initialization"
git tag -a v0.9.5.2 -m "Sentinel v0.9.5.2 - OCR Provider Architecture Stabilization"
git push origin main
git push origin v0.9.5.2
```
