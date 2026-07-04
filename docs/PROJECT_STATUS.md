# Project Status – Sentinel v0.9.5.91

**Current sprint:** v0.9.5.91 Rank Context & Window Merge Hardening  
**Baseline:** Sentinel v0.9.5.90  

Sentinel remains in the Data Quality before Intelligence phase. The 549–555 full benchmark changed the diagnosis: OCR/power recovery is no longer the only or main risk. The critical P0 finding is that rows without reliable visible-rank evidence can be promoted by merge order and power sorting, causing cross-window contamination and corrupt Operational Truth. v0.9.5.91 hardens the merge layer accordingly.

## Current guarantees

- Screenshot observations remain the only Ground Truth for benchmark review.
- Rows with explicit visible rank evidence keep that visible slot as `final_rank` / `operational_rank`.
- Rows missing visible rank evidence inside an otherwise ranked context are not promoted to normal Operational Truth.
- Cross-window duplicate visible-rank conflicts are diagnosed instead of being decided by power.
- Diagnostics include `window_id`, `rank_context_status`, `final_rank`, `merge_reason` and `rank_warning`.

## Current known risks

- Full 549–555 remains a review benchmark, not a verified Operational Truth baseline.
- The Ground Truth Validator intentionally covers only Server 551 THP as the Gold-Standard file; extending it to all servers would require high manual effort.
- OCR still produces known power families (`alliance_high_explosion`, `thp_high_explosion`, `thp_low_truncation`), but these are now secondary to rank/window integrity.

## Next focus

- Re-run 549–555 with cache off and inspect whether unranked top-window rows are held as diagnostics instead of shifted into false ranks.
- Route merge diagnostics into explicit Review/Quarantine surfaces instead of only keeping them as export diagnostics.
- Begin v0.9.5.92 Identity Integrity: alliance-tag drift, duplicate identity and Unicode canonicalization.

---

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
