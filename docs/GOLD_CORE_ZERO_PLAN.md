# Gold Core Zero Plan

## Current phase: v0.9.5.145 — Gold Core Zero I

### Objective
Reduce Gold Core blockers through one evidence class at a time, with measurable benchmark results and no modification of Operational Truth.

### Lane 1: Vote Selection Policy
A warning-only vote case may be cleared only when all conditions are true:

1. The match is accepted and is not a context-gap inference.
2. At least one current-snapshot evidence fragment carries `vote_outside_allowed_set`.
3. Every affected fragment selected the expected glyph and is `verified_expected`.
4. No observed, unresolved, ambiguous, crop-field-mismatch, or power-column-bleed evidence exists.
5. The expected player display is exact.
6. Alliance identity and power independently match.

All decisions remain validator-side evidence assessments. OCR export, Ground Truth and Operational Truth are unchanged.

### Acceptance
- Existing Gold Core regression suite remains green.
- New policy stop-sign tests remain green.
- Server 551 benchmark shows whether the vote-selection cluster decreases.
