# Project Status – Sentinel v0.9.5.93

**Current sprint:** v0.9.5.93 Review Export Separation & Identity Fidelity Guard  
**Baseline:** Sentinel v0.9.5.92

Sentinel remains in Data Quality before Intelligence. v0.9.5.92 proved that Server 551 can produce complete operational rows again: Alliance Power exported ranks 1-21 cleanly, THP exported ranks 1-101 cleanly, and the Server 551 THP Ground Truth validator reported 50/50 matched rows, 0 missing rows and 0 bad matches.

The remaining defect was review leakage: `PENDING REVIEW` placeholders appeared as normal THP ranks 102-105. v0.9.5.93 separates review placeholders from Operational Truth exports and console summaries. Quarantined rows remain available in `REVIEW/ranking_guard_quarantine`, Review Dashboard and Evidence Pack, but they no longer become artificial ranking rows.

A second lesson is now P0 for V1: matching a row is not the same as preserving identity. `Joncollins21` vs `Joncollinszl` and `DAY` vs `daY` are not harmless OCR variations. v0.9.5.93 introduces initial Identity Guard metadata so Sentinel can distinguish OCR similarity from exact historical identity fidelity.

## Current quality signal

- Server 551 THP Ground Truth after v0.9.5.92: 50/50 matched, 0 missing, 0 bad matches.
- Remaining export issue: review placeholders leaked into normal operational sheets as synthetic ranks.
- Identity issue: exact alliance tags are case-sensitive and player names must preserve digit/letter fidelity for future transfer tracking.

## Current P0 focus

1. Keep review/quarantine rows out of normal Operational Truth sheets.
2. Preserve Recall 1.0 while improving export precision.
3. Treat alliance tags as case-sensitive Last War identifiers.
4. Surface Identity Fidelity risk instead of silently relying on fuzzy matching.
5. Continue screenshot-first validation; exports are never ground truth.
