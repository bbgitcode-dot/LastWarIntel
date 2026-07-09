# Project Status – Sentinel v0.9.5.137

**Current release:** v0.9.5.137 Character Acquisition Engine Phase I  
**Functional baseline:** v0.9.5.136 Gold Accuracy Mode  
**Sprint posture:** Gold Accuracy / evidence acquisition over runtime optimization

## Current assessment

Sentinel's structural identity pipeline is stable: Ranking Guard, Data Guard, Gap Recovery, Alignment Intelligence, Display Reconstruction, Promotion Guard and the Evidence Scheduler are mature enough that the next quality gains come from better character evidence acquisition, not more global scheduling or promotion logic.

## What v0.9.5.137 adds

- Character Acquisition Engine Phase I.
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

`v0.9.5.138 – Multi-Crop Consensus` should use the new acquisition report to gather richer observations per weak character position. The objective is to improve the 15 remaining Gold-Core blockers by increasing character evidence quality rather than adding new decision gates.
