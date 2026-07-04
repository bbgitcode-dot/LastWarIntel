# Project Status – Sentinel v0.9.5.90

**Current sprint:** v0.9.5.90 Operational Truth Hardening  
**Baseline:** Sentinel v0.9.5.89  

Sentinel remains in the Data Quality before Intelligence phase. The 549–554 benchmark proved that cache-off OCR validation works as a diagnostic, but it also exposed a critical risk: recovered power could move a row away from its visible screenshot rank and normalized identity could hide the raw display. v0.9.5.90 hardens those invariants.

## Current guarantees

- Explicit visible rank slots are preserved as operational rank.
- Quarantined/review rows do not collapse following ranks.
- Raw player/alliance identity is stored separately from normalized identity.
- Ambiguous recovery candidates remain review evidence and do not become Operational Truth.
- High-explosion OCR values are removed from operational power when held for review.

## Remaining focus

- Clean up stale smoke command-stub tests and OCR config compatibility tests so full smoke collection is trustworthy again.
- Re-run the complete 549–554 benchmark with .90 and compare Server 553 THP visually, especially `[SWSq] sven the vän`.
- Continue reducing review count only after the slot and raw identity invariants hold reproducibly.
