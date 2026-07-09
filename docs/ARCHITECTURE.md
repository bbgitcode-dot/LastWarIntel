# v0.9.5.140 – Gold Regression & Strike II

- Adds permanent GC-001 Joncollins21 Gold-Core regression metadata.
- Extends Gold-Core elimination with Strike II: one missing Latin glyph plus optional known local glyph confusion, only when Rank/Power/Core Alliance anchors are proven.
- Keeps context gaps read-only and never modifies Operational Truth.
- Report phase label: `v0.9.5.140_gold_regression_strike_ii`.

# Sentinel Architecture

**Current version:** v0.9.5.140

## Gold Accuracy Architecture

Sentinel is now structured as an evidence-first identity pipeline:

```text
OCR / Raw Export
  ↓
Ranking Guard
  ↓
Data Guard
  ↓
Alignment Intelligence
  ↓
Character ReOCR
  ↓
Character Acquisition Engine
  ↓
Display Reconstruction
  ↓
Evidence Confidence / Promotion Guard
  ↓
Reports / Decision Support
```

## Character Acquisition Engine

The v0.9.5.140 Character Acquisition Engine converts individual Character ReOCR fragments into scored observations and per-position consensus. It produces:

- observation confidence,
- vote consensus,
- crop quality,
- consensus status,
- position heatmap,
- row-level acquisition coverage metrics.

This layer is strictly read-only. It does not mutate Operational Truth, snapshots, exports, Ground Truth, or verified display fields. Its purpose is to increase evidence quality for later Gold-Core blocker elimination.


## Gold Core Elimination Gate

v0.9.5.140 adds a validator-side elimination gate after Display Reconstruction and before final benchmark summaries. It may mark a Gold Core blocker as cleared only when current-run evidence satisfies strict guardrails: exact reconstructed display name, proven Core Alliance, power match, promotion eligibility, no unresolved/observed character evidence, and no context gap.

This is an Evidence Layer decision. Operational Truth remains unchanged.


## v0.9.5.140 – Gold Blocker Strike I

This release turns Gold-Core elimination from classification into a first targeted strike. It adds a narrow validator-side clearance path for localized Latin single-glyph blockers when every other identity anchor is already proven: non-context row, power match, core alliance proof, promotion eligibility, non-blocked evidence confidence, and one-character Latin display drift. Operational Truth remains unchanged; the clearance only affects benchmark evidence status and is fully reported.

Key changes:
- Added `clear_gold_core_blocker_strike_i` action.
- Added single-glyph Latin blocker clearance guard.
- Updated Gold-Core elimination phase labels to `v0.9.5.140_gold_blocker_strike_i`.
- Preserved context-gap read-only policy and DataGuard protections.
