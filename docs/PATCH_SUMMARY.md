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
