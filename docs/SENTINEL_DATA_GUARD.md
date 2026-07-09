# v0.9.5.140 – Gold Regression & Strike II

- Adds permanent GC-001 Joncollins21 Gold-Core regression metadata.
- Extends Gold-Core elimination with Strike II: one missing Latin glyph plus optional known local glyph confusion, only when Rank/Power/Core Alliance anchors are proven.
- Keeps context gaps read-only and never modifies Operational Truth.
- Report phase label: `v0.9.5.140_gold_regression_strike_ii`.

# Sentinel Data Guard

**Current release:** v0.9.5.140

## Principle

Evidence before inference. Inference before promotion. Promotion never modifies Operational Truth unless explicitly allowed by a future, guarded, auditable mechanism.

## v0.9.5.140 Guardrail

Gold Core Elimination Phase I is evidence-only. It may score character observations, build consensus, and report weak positions, but it must not:

- rewrite player names,
- rewrite alliance tags,
- modify snapshots,
- modify Ground Truth,
- modify exports,
- bypass Ranking Guard or Promotion Guard.

The new `character_acquisition_report.json/xlsx` exists to improve explainability and future blocker resolution while preserving Data Guard invariants.


## v0.9.5.140 DataGuard Note

Gold Core Elimination is permitted only as benchmark evidence classification. It must not promote context-gap inference, must not write reconstructed display values into Operational Truth, and must preserve the original OCR/Ground Truth evidence trail.


## v0.9.5.140 – Gold Blocker Strike I

This release turns Gold-Core elimination from classification into a first targeted strike. It adds a narrow validator-side clearance path for localized Latin single-glyph blockers when every other identity anchor is already proven: non-context row, power match, core alliance proof, promotion eligibility, non-blocked evidence confidence, and one-character Latin display drift. Operational Truth remains unchanged; the clearance only affects benchmark evidence status and is fully reported.

Key changes:
- Added `clear_gold_core_blocker_strike_i` action.
- Added single-glyph Latin blocker clearance guard.
- Updated Gold-Core elimination phase labels to `v0.9.5.140_gold_blocker_strike_i`.
- Preserved context-gap read-only policy and DataGuard protections.
