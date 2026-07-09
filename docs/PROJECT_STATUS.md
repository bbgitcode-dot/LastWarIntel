# Project Status – Sentinel v0.9.5.139

**Current release:** v0.9.5.139 Gold Core Elimination Phase I  
**Functional baseline:** v0.9.5.136 Gold Accuracy Mode  
**Sprint posture:** Gold Accuracy / evidence acquisition over runtime optimization

## Current assessment

Sentinel's structural identity pipeline is stable: Ranking Guard, Data Guard, Gap Recovery, Alignment Intelligence, Display Reconstruction, Promotion Guard and the Evidence Scheduler are mature enough that the next quality gains come from better character evidence acquisition, not more global scheduling or promotion logic.

## What v0.9.5.139 adds

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


## v0.9.5.139 Functional Outcome

The sprint moves from diagnostics to functional Gold-Core elimination. Sentinel now has an evidence-only gate that can reduce Gold Core blockers when display reconstruction is strong enough to prove Core Identity. The gate updates benchmark validation status only; it does not write to snapshots, exports, Ground Truth, or Operational Truth.

Next work: run Server 551 regression and inspect `gold_core_elimination_report.*` to verify how many of the 15 blockers are actually cleared.

## v0.9.5.139 – Gold Blocker Strike I

This release turns Gold-Core elimination from classification into a first targeted strike. It adds a narrow validator-side clearance path for localized Latin single-glyph blockers when every other identity anchor is already proven: non-context row, power match, core alliance proof, promotion eligibility, non-blocked evidence confidence, and one-character Latin display drift. Operational Truth remains unchanged; the clearance only affects benchmark evidence status and is fully reported.

Key changes:
- Added `clear_gold_core_blocker_strike_i` action.
- Added single-glyph Latin blocker clearance guard.
- Updated Gold-Core elimination phase labels to `v0.9.5.139_gold_blocker_strike_i`.
- Preserved context-gap read-only policy and DataGuard protections.
