# Sentinel v0.9.5.115 Patch Summary

## Focus
Latin Player Name Core Resolution.

## What changed
- Local Glyph Gate now accepts narrow Latin-only missing-glyph targets, e.g. `Mizzenmast -> Mzzenmast`.
- Pure Latin spacing gaps can be treated as verified formatting evidence instead of blocking Core Identity.
- Mixed CJK/Hangul/Kana display drift remains conservative and is still skipped/nonlocal.

## Why
The v0.9.5.114 run showed that alliance tags are mostly solved and remaining Core blockers are primarily player-name display drift. v0.9.5.115 focuses on Latin names where the current screenshot can still prove the missing glyph without historical identity data.

## Validation
- 12 targeted smoke tests passed.
- `py_compile` passed for validator and targeted ReOCR modules.

## v0.9.5.116 – Latin Name Block Reconstruction

- Added screenshot-local Latin Name Block Reconstruction for aligned Latin-only player names where single-glyph ReOCR is too weak, e.g. missing/shifted characters such as `Mizzenmast -> Mzzenmast`, `Drpeek -> Ieek`, and spacing/digit drifts like `N E R D -> NER0`.
- Reconstruction is DATAGUARD-gated: it only runs on accepted/aligned rows, does not use historical identity data, and refuses mixed CJK/Hangul/Kana display drift.
- Added reconstruction evidence to the existing character ReOCR debug stream with crop strategy `latin_name_block`, candidate text, selected reconstruction, confidence, and timing.
- Core Identity can now accept a verified Latin name block when the whole-name OCR candidate supports the expected display more strongly than the observed OCR string.
