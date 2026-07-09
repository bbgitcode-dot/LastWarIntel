# Sentinel Data Guard

**Current release:** v0.9.5.127  
**Functional baseline:** v0.9.5.127

## Prime directive

DataGuard protects Operational Truth.

It may collect evidence, classify risk, quarantine rows, accept read-only inference, and request review. It must not silently rewrite player or alliance identities.

## Current rules

1. OCR output is evidence, not truth.
2. Ground Truth is benchmark reference, not mutable operational data.
3. Context gaps are not character drift.
4. Character ReOCR is evidence-only unless a downstream validator explicitly counts it as verified display evidence.
5. Cached ReOCR evidence is allowed only inside the same validation run and only for exact target/text pairs.
6. No historical player identity memory is used to “fix” current screenshot names.
7. Operational Truth remains unchanged by validation reports.

## Safe behavior examples

### Safe local glyph proof

`Joncollinszl` can become verified display `Joncollins21` when screenshot-local ReOCR proves `z -> 2` and `l -> 1`.

### Unsafe context gap

`K9 Thunder` vs `YUNS` must not be treated as glyph drift. If rank/power context supports a gap, inference may mark it read-only, but Character ReOCR must not try to repair it as a name typo.

### Safe cache reuse

If `[PbC]` case-sensitive evidence has already been verified for an exact target/text pair inside one validation run, v0.9.5.124 may reuse that evidence as `evidence_cache_hit`. The report must mark that it is reused evidence, not a fresh crop read.

## Current next guardrail

The next functional sprint must reduce the 15 Gold Core blockers without weakening these rules.


## v0.9.5.126 guardrail

Gold Core blocker classification is diagnostic. A row can receive a proposed fix lane without becoming Operational Truth. `observed_text_confirmed`, `crop_geometry_problem`, and `context_gap_read_only` remain strict stop signs.


## v0.9.5.127 guardrail

The Gold Core Resolution Plan is planning-only. It may mark a row as a local automation candidate, but it does not promote display text into Operational Truth. Crop geometry problems, observed-text-confirmed rows, nonlocal script display rows, and context gaps remain hard stop signs until their own evidence path is implemented.

## v0.9.5.128 DataGuard Note

Alignment Intelligence is read-only. `verification_allowed_read_only` means Sentinel may produce diagnostic evidence for a high-confidence Context Gap, not that it may alter Ground Truth, snapshots, exports, or database state. Operational Truth remains the write boundary.
## v0.9.5.129 Road-to-V1 Update – Read-only Evidence Execution

The Alignment Intelligence lane now executes evidence-only verification for eligible Context Gap rows. This improves explainability without weakening DataGuard. The next V1-critical step is not automatic correction; it is an explicit evidence consumption policy that separates review recommendations from Operational Truth.



## v0.9.5.131 DataGuard Note

Display Reconstruction is explicitly read-only. It may propose `display_reconstructed_name` and `display_reconstructed_alliance_tag` in reports, but it may not write to Operational Truth, snapshots, Ground Truth, or verified display fields. Any future promotion path must be implemented as a separate guarded export policy.

## v0.9.5.132 DataGuard Note – Display Promotion Guard

Display Reconstruction Guard formalizes that reconstructed display strings are evidence products, not Operational Truth. Unsafe display-name promotion is blocked when the evidence base is insufficient, while safe partial evidence such as alliance-tag reconstruction may still be reported. No Ground Truth, snapshot, export, or verified display field is silently changed.
