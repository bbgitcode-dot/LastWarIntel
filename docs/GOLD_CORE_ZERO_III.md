# Gold Core Zero III — Evidence-Bound Name Reconstruction

Version: `0.9.5.147`

## Purpose

Gold Core Zero III replaces the circular requirement that a name must already be exact before character evidence may prove it. The validator now distinguishes exact source text from a complete evidence reconstruction.

## Proof states

- `SOURCE_EXACT`
- `EVIDENCE_RECONSTRUCTED_EXACT`
- `PARTIAL_RECONSTRUCTION`
- `CONFLICTING_EVIDENCE`
- `INSUFFICIENT_EVIDENCE`
- `UNKNOWN`

## Evidence rule

Every expected name position must be proven by either:

1. an equal character aligned from the current-snapshot source display; or
2. a position-bound `verified_expected` ReOCR fragment whose selected glyph equals the expected glyph.

Ground Truth is only the comparison target. It is never used to fill an unobserved position. Missing positions remain explicit in the reconstructed diagnostic value as `?`.

## Clearance rule

`clear_gold_core_blocker_evidence_reconstructed_name` is allowed only when:

- the row is a Gold Core blocker with a vote-warning evidence signature;
- matching, alliance, and power anchors are proven;
- context is available;
- expected-only vote consensus exists;
- there is no observed, unresolved, crop, or field-mismatch evidence;
- name coverage is exactly 100 percent;
- the complete reconstruction equals the expected display;
- no Ground-Truth-only fill was used.

Operational Truth, OCR export rows, screenshots, and Ground Truth remain unchanged.
