# Gold Core Zero Plan — v0.9.5.148

## Benchmark decision

Gold Core Zero III did not clear any `vote_warning_gate_review` case. The planned distinction between `SOURCE_EXACT` and `EVIDENCE_RECONSTRUCTED_EXACT` remains valid conceptually, but the benchmark generated no complete evidence reconstruction.

## Next lane: Position Evidence Completion

1. Enumerate missing positions for ranks 8, 11, 41, 48 and 50, the five vote-warning cases.
2. Acquire narrowly targeted crops for those positions from current screenshots.
3. Reject field bleed before character voting.
4. Require full position coverage and zero conflicts.
5. Never fill from Ground Truth or historical names.
6. Preserve UNKNOWN until a complete screenshot-derived base exists.

## Stop signs

- UNKNOWN base;
- incomplete position coverage;
- conflicting evidence;
- unresolved votes;
- observed counterevidence;
- crop-field mismatch;
- missing alliance or power proof.

---

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

## Observability Gate — v0.9.5.149

Before any further clearance strategy, Sentinel must identify the exact blocking character positions and their evidence state. The next implementation may target evidence acquisition only where the .149 reports prove missing or unresolved coverage. Conflicts remain a separate non-clearable lane until stronger screenshot evidence resolves them.
