# Architecture

## v0.9.5.150 evidence-provenance layer

After the Gold-Core Character Position Evidence Map, Sentinel builds a read-only provenance graph for every blocked character position:

Screenshot reference → Crop geometry → OCR observation → Vote resolution → Evidence reconstruction → Promotion Guard

The layer identifies the first failed stage while preserving the full downstream consequence chain. It emits diagnostic reports only and cannot alter source rows, reconstructed display values, clearance decisions, Ground Truth, or Operational Truth.

# Sentinel Architecture — v0.9.5.148

```text
Screenshot
  ↓
OCR
  ↓
Evidence
  ↓
Character Acquisition
  ↓
Character Position Intelligence
  ↓
Display Reconstruction
  ↓
Inference
  ↓
Ground Truth Validation
  ↓
Gold Core
  ↓
Strategic Intelligence
```

## Name proof states

- `SOURCE_EXACT`: the current source display itself proves the exact name.
- `EVIDENCE_RECONSTRUCTED_EXACT`: every name position is proven from current-screenshot evidence with no conflicts or missing positions.
- Partial, conflicting, insufficient, UNKNOWN, or Ground-Truth-filled states are not exact proof.

Display Reconstruction is evidence assembly, not correction. Ground Truth is used to validate outcomes, never to supply characters. Promotion Guard remains the final safety gate before any Gold-Core clearance.

---

# v0.9.5.141 – Character Position Intelligence Phase I

- Implements functional Character Position Intelligence in the validator, not just report scaffolding.
- Adds `character_position_intelligence_report.json/xlsx` with position-level risk, action, and rank-level acquisition focus.
- Feeds weak/critical position decisions into the Evidence Scheduler so Gold Accuracy prioritizes problematic character positions.
- Keeps Display Reconstruction, Strike clearance, Context Gaps, and Operational Truth read-only.
- Report phase label: `v0.9.5.141_character_position_intelligence`.

# v0.9.5.140 – Gold Regression & Strike II

- Adds permanent GC-001 Joncollins21 Gold-Core regression metadata.
- Extends Gold-Core elimination with Strike II: one missing Latin glyph plus optional known local glyph confusion, only when Rank/Power/Core Alliance anchors are proven.
- Keeps context gaps read-only and never modifies Operational Truth.
- Report phase label: `v0.9.5.140_gold_regression_strike_ii`.

# Sentinel Architecture

**Current version:** v0.9.5.141

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

## Position-Bound Gold-Core Evidence Intelligence (v0.9.5.149)

After Evidence Reconstruction, a read-only diagnostics layer builds a Character Position Evidence Map for every remaining Gold-Core blocker. It consumes current-snapshot source alignment and Character ReOCR evidence, emits per-position provenance and a cross-case heatmap, and cannot modify Operational Truth or clearance decisions. Ground Truth is comparison context only.

## v0.9.5.152 – Source-Bound Display Reconstruction

Display Reconstruction now preserves a read-only provenance object per character. Base OCR characters retain screenshot/source-row and character-offset provenance; crop-bound Character ReOCR evidence retains its stronger crop chain. These links improve explainability and acquisition diagnostics but never become Gold-authoritative by themselves. Authoritative Gold-Core root-cause metadata is joined through the blocker report rather than the generic validation match status.
