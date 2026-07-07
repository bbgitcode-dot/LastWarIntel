# Patch Summary – v0.9.5.119 Latin Residual Core Blocker Cleanup

## Ziel

`.119` greift die verbleibenden Latin-only Core-Blocker nach `.118` an. Der Patch löst keine breiten fehlenden Namen per Guessing, sondern klassifiziert nur sichere Fälle, bei denen Server/Power/Alliance bereits stabil sind und der erwartete Latin-Core im OCR-Ergebnis sichtbar enthalten ist.

## Änderungen

- Neuer Latin Residual Core Identity Gate im Ground Truth Validator.
- Neue Felder:
  - `latin_residual_core_identity_match`
  - `latin_residual_core_identity_resolution`
  - `latin_residual_policy_reason`
- Neue JSON-/Excel-Reports:
  - `latin_residual_policy_summary`
  - `latin_residual_policy_rows`
  - `latin_residual_policy`
  - `latin_residual_rows`
- Full Display bleibt streng: ein Latin-Residual-Match ist keine Display-Exaktheit.
- Konservative Ablehnung für breite Missing-Glyph-Fälle wie `Drpeek -> Ieek`, `N E R D -> NER0`, `S I G I -> 5161...`.

## Erwartung

- `verified_core_identity_matches` kann bei sicheren Latin-only Residual-Fällen steigen.
- `gold_core_blocker_rows` sollte sinken, aber nur dort, wo die Identität operativ robust ist.
- Die restlichen Core-Blocker werden danach klarer aufgeteilt in:
  - echte Latin-OCR/Reconstruction-Probleme,
  - nicht stabile Mixed-Script-Fälle,
  - Alignment-/Context-Gaps.

## Validation

```text
21 passed – Latin Residual Core / Non-Latin Policy / Reconstruction Gate / Gold Gate
py_compile OK
zip integrity OK
```
