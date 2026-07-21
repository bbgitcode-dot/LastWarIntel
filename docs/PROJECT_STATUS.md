# v0.9.5.142 – Gold Core Strike III

## Functional changes

- Adds a conservative Strike III validator gate for one or two Latin substitutions that belong exclusively to known OCR glyph-confusion families.
- Requires accepted same-snapshot identity matching, exact power anchor, proven Core Alliance, Promotion Guard eligibility, zero unresolved fragments, zero observed votes, and confirmed character evidence for every changed position.
- Blocks identity guessing, arbitrary fuzzy substitutions, insertion/deletion shapes, context-gap inference and unstable Character Position Intelligence states.
- Preserves Operational Truth, Ground Truth, snapshots and exports unchanged.
- Adds dedicated Strike III smoke regressions while retaining Strike I/II coverage.

## Validation

- Targeted Gold-Core regression suite: 12 passed.
- The legacy full smoke suite is not clean in the supplied .141 baseline because it contains two shell-command files saved as Python tests and obsolete OCR configuration imports. These pre-existing collection defects were not masked or rewritten in this sprint.

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

# Project Status – Sentinel v0.9.5.140

**Current release:** v0.9.5.141 Gold Core Elimination Phase I  
**Functional baseline:** v0.9.5.136 Gold Accuracy Mode  
**Sprint posture:** Gold Accuracy / evidence acquisition over runtime optimization

## Current assessment

Sentinel's structural identity pipeline is stable: Ranking Guard, Data Guard, Gap Recovery, Alignment Intelligence, Display Reconstruction, Promotion Guard and the Evidence Scheduler are mature enough that the next quality gains come from better character evidence acquisition, not more global scheduling or promotion logic.

## What v0.9.5.140 adds

- Gold Core Elimination Phase I.
- `character_acquisition_report.json/xlsx`.
- Per-observation confidence from OCR confidence, vote consensus, crop quality and target status.
- Per-position character consensus across observations.
- Character position heatmap for recurring weak glyph positions.
- Read-only detail metrics: acquisition positions, verified/probable/unresolved positions and average acquisition confidence.

## Guardrails

- Operational Truth remains locked.
- Ground Truth is not modified.
- Snapshot/export values are not silently changed.
- Character Acquisition produces evidence only; promotion remains controlled by Display Reconstruction Guard and Promotion Guard.

## Next recommended sprint

`v0.9.5.140 – Multi-Crop Consensus` should use the new acquisition report to gather richer observations per weak character position. The objective is to improve the 15 remaining Gold-Core blockers by increasing character evidence quality rather than adding new decision gates.


## v0.9.5.140 Functional Outcome

The sprint moves from diagnostics to functional Gold-Core elimination. Sentinel now has an evidence-only gate that can reduce Gold Core blockers when display reconstruction is strong enough to prove Core Identity. The gate updates benchmark validation status only; it does not write to snapshots, exports, Ground Truth, or Operational Truth.

Next work: run Server 551 regression and inspect `gold_core_elimination_report.*` to verify how many of the 15 blockers are actually cleared.

## v0.9.5.140 – Gold Blocker Strike I

This release turns Gold-Core elimination from classification into a first targeted strike. It adds a narrow validator-side clearance path for localized Latin single-glyph blockers when every other identity anchor is already proven: non-context row, power match, core alliance proof, promotion eligibility, non-blocked evidence confidence, and one-character Latin display drift. Operational Truth remains unchanged; the clearance only affects benchmark evidence status and is fully reported.

Key changes:
- Added `clear_gold_core_blocker_strike_i` action.
- Added single-glyph Latin blocker clearance guard.
- Updated Gold-Core elimination phase labels to `v0.9.5.140_gold_blocker_strike_i`.
- Preserved context-gap read-only policy and DataGuard protections.

## Previous sprint: v0.9.5.143 – Gold Core Strike IV

The Gold Core phase now includes read-only root-cause analytics and persistent failure memory. The next benchmark run on server 551 should be used to measure the remaining blocker distribution and select the highest-impact path toward Gold Core Zero.

## v0.9.5.144 status – Gold Core Strike V

Gold Core Root Cause Truth is consolidated. Established blocker classification now leads
analytics, and every case can be traced through one stable case ID, Failure Memory,
prioritized recommendation, and cross-report explorer. The next phase is targeted
Gold Core elimination based on the generated action plan, not further analytics scaffolding.

## v0.9.5.145 Status — Gold Core Zero I

Gold Core knowledge consolidation is complete enough to begin targeted elimination. The first elimination lane is Vote Selection Policy. `.145` introduces a narrow, deterministic warning downgrade for expected-only vote noise. It does not relax crop, identity, script, or counterevidence safeguards. The next benchmark determines the actual blocker reduction and which remaining root-cause lane should be addressed next.

