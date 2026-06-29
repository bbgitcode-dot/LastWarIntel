# Sentinel v0.9.5.5 – EasyOCR Baseline Calibration

## Purpose

Calibrate the EasyOCR transfer-baseline pipeline after the first real benchmark.
The goal is to reduce false REVIEW noise while keeping genuinely unsafe rows in review.

## Changed

- Added calibrated player identity quality parser.
- Prefix noise before `[TAG]` is now treated as a correction, not an automatic review.
- CJK player names are accepted as valid when OCR returns usable characters.
- Missing alliance tags are recorded as warnings but no longer automatically invalidate a row.
- Missing OCR rank no longer creates a `rank_warning` for every row.
- Rank warnings now focus on actual OCR evidence: rank mismatches and observed rank gaps.
- Warzone consensus with at least three matching detections no longer propagates row-level server warnings.

## Why

The previous pipeline was too conservative:

- 100% of THP rows were REVIEW.
- Every row received a rank warning when OCR rank was missing.
- Accepted server consensus still created many server warnings.

This patch makes the quality gate actionable instead of noisy.

## Expected Result

After re-running EasyOCR:

- VALID rows should appear again.
- REVIEW rows should represent truly problematic identities.
- Rank warnings should highlight real integrity issues instead of design noise.
- Server warnings should be reserved for screenshots that actually require attention.

The Sentinel approves.
