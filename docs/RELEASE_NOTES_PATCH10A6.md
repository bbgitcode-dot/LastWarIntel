# Sentinel v0.9.4-pre – Patch 10A.6

## Transfer Baseline OCR Stability Hotfix

This patch stabilizes the S6 pre-transfer import after multilingual OCR caused metadata detection regressions and crashes.

## Added

- Separate metadata OCR path using stable English-only OCR.
- Configurable OCR profiles:
  - `fast` profile for normal CPU baseline imports.
  - `full` profile for targeted multilingual review.
- Screenshot-level Warzone consensus validation.
- Server review handling when Warzone cannot be validated.
- OCR rank preservation with separate `ocr_rank` and `computed_rank`.
- Rank integrity warnings for missing ranks and OCR/computed-rank mismatch.
- Server quality metadata in Excel export.

## Fixed

- Prevents crashes when `server=None`.
- Prevents multilingual OCR noise from breaking Warzone detection.
- Prevents missing OCR rows from being silently hidden by `n+1` rank assignment.

## Operational Notes

Default runtime profile is now `fast`:

```bash
python main.py
```

For targeted slow review with all supported language groups:

```bash
set SENTINEL_OCR_PROFILE=full
python main.py
```

## Git

```bash
git add .
git commit -m "fix(data-quality): stabilize OCR metadata and rank integrity"
git tag -a v0.9.4-pre-ocr-stability -m "Sentinel v0.9.4-pre - OCR Metadata Stability Hotfix"
git push origin main
git push origin v0.9.4-pre-ocr-stability
```

## Sentinel Principle

Reliable Intelligence begins with reliable data.
