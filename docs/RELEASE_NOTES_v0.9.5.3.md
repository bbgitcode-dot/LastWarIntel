# Sentinel v0.9.5.3 - OCR Benchmark Finalization Hotfix

## Fixed

- Fixed Windows console Unicode crashes when printing OCR names containing Asian characters.
- Added UTF-8 stdout/stderr configuration with safe fallback printing.
- Updated PaddleOCR provider for PaddleOCR 3.x API changes.
- Removed dependency on legacy `ocr(..., cls=False)` calls.
- Added flexible PaddleOCR result normalization for v3 result objects and legacy v2 list outputs.

## Goal

The benchmark should now complete far enough to produce actual EasyOCR and PaddleOCR quality metrics instead of failing on provider/runtime compatibility issues.

## Engineering Principle

Reliable engineering begins with measurable results.
