# Patch Summary – v0.9.5.118 Non-Latin Identity Policy Gate

## Ziel

`.118` trennt Full Display Fidelity von operativer Core Identity für gemischte Latin/CJK/Hangul-Spielernamen. Sentinel darf diese Namen weiterhin nicht als exakt gelesen markieren, kann aber den Core-Identity-Gate passieren lassen, wenn Server/Power/Alliance und stabiler Latin-Core sicher sind.

## Änderungen

- Neuer Script-Limited Identity Policy Gate im Ground Truth Validator.
- Neue Felder: `script_limited_core_identity_match`, `script_limited_core_identity_resolution`, `script_limited_policy_reason`, `identity_policy_class`.
- Neue Reportbereiche: `script_limited_policy_summary` und `script_limited_policy_rows`.
- Mixed Latin/CJK/Hangul bleibt konservativ: kein `verified_name_display_exact_match`, keine Operational-Truth-Änderung.
- Latin-only Glyph- und Block-Reconstruction aus `.117` bleibt unverändert.

## Erwartung

- `verified_core_identity_matches` kann steigen, ohne Full Gold fälschlich freizugeben.
- `gold_core_blocker_rows` sinkt bei stabilen Mixed-Namen mit sicherem Latin-Core.
- Full Display Gold bleibt blockiert, solange nicht alle Zeichen exakt verifiziert sind.

---

## v0.9.5.117 – Reconstruction Candidate Gate

This patch sharpens the v0.9.5.116 Latin Name Block Reconstruction path. Whole-name block OCR now runs only when a Latin-only row is aligned, power/alliance-safe, and still has unresolved player-name glyph evidence after the cheaper local-glyph pass.

Expected impact: keep the +Core Identity gains from block reconstruction while cutting avoidable long OCR passes for names already solved by glyph verification.

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
