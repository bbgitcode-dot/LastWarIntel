# Patch 10A.3 - Multilingual OCR Foundation

## Purpose

Prepare Sentinel's S6 pre-transfer baseline import for multilingual player names.

Reliable Intelligence begins with reliable data.

## Added

- Configurable OCR language list
- Default multilingual OCR profile:
  - English
  - Simplified Chinese
  - Traditional Chinese
  - Japanese
  - Korean
- Environment override via `SENTINEL_OCR_LANGUAGES`
- GPU override via `SENTINEL_OCR_GPU`
- English fallback if multilingual EasyOCR initialization fails
- Smoke test for OCR language configuration

## Changed

- Removed hardcoded `easyocr.Reader(["en"])`
- OCR import is now lazy so non-OCR tests do not require EasyOCR to be installed

## Operational Instructions

After rollout:

1. Run a full reimport of all S6 pre-transfer screenshots.
2. Do not use incremental import for the baseline.
3. Compare UNKNOWN/REVIEW rates against the previous export.
4. Verify that alliance tags still parse correctly.
5. Freeze the pre-transfer baseline only after review.

## Git

```bash
git add .
git commit -m "feat(ocr): add multilingual OCR foundation"
git tag -a v0.9.4-pre-ocr-multilingual -m "Sentinel v0.9.4-pre - Multilingual OCR Foundation"
git push origin main
git push origin v0.9.4-pre-ocr-multilingual
```

The Sentinel approves.
