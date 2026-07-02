# Sentinel Project Status

**Current Version:** v0.9.5.52  
**Sprint Type:** Digit-Preserving Power Recovery  
**Runtime Baseline:** v0.9.5.52 – Segment Order Recovery Guardrails  
**Current Phase:** Data Integrity Fortress / Operational Data Stability  
**Next Planned Sprint:** v0.9.5.52 – Import Session and Segment Integrity

---

## Executive summary

Sentinel v0.9.5.51 hardens the v0.9.5.50 candidate decision engine with digit-preserving recovery metadata and scoring. v0.9.5.49 made high power explosion recovery safe by removing legacy fallback decisions; v0.9.5.50 adds the missing opposite direction: low/truncated THP powers such as 32M, 25M, 23M, 19M, and 13M can now generate x10, x100, and inserted-zero candidates.

The sprint keeps the same doctrine: recovery is allowed only when source-local context and OCR-error probability produce a clear candidate margin. Ambiguous values remain quarantined.

---

## What changed in v0.9.5.51

Sentinel now adds an explicit digit-preservation score to low/truncated THP power recovery. This addresses the .50 finding that a candidate can be locally plausible but still distort the visible OCR digit sequence.

### Added

- `digit_preservation_score` in power recovery candidate metadata.
- `digit_preservation:*` reasons in candidate traces and export/report metadata.
- A digit-preserving low-truncation decision path for narrow but clear candidate margins.

### Guardrail

Digit preservation is a scoring signal, not a truth override. Data Guard, Ranking Guard, source-local context, and quarantine-first behavior remain authoritative.

## What changed in v0.9.5.50

### Added

- Low/truncated THP candidate generation for OCR values that lost a magnitude digit.
- Candidate transforms for `scale_x10_truncated_digit`, `scale_x100_truncated_digit`, and `insert_zero`.
- OCR error probability scoring for high THP leading-digit explosions such as `764M -> 164M` and `798M -> 198M`.
- Regression tests covering Server 549–553 findings: high explosion recovery, low truncation recovery, and Alliance Power tail protection.

### Guardrail

- The model is source-local and ranking-type aware.
- Alliance Power low tails are not treated as THP truncation errors.
- Ground Truth informs the error classes during development but does not power runtime decisions.


## What changed in v0.9.5.49

The remaining legacy leading-digit recovery decision fallback has been removed. Sentinel may still generate leading-digit candidates, but it no longer chooses a recovered value merely because a legacy rule can produce one.

The new decision path is:

```text
Candidate Generator
    ↓
Context Scoring
    ↓
Margin Decision Engine
    ↓
Recover only clear winners, quarantine ambiguous ties
```

This is intentionally stricter. Server 553 showed several cases where the selected legacy recovery was not the best scored candidate or where the margin was effectively zero. v0.9.5.49 now treats those cases as review-worthy uncertainty.

## What changed in v0.9.5.48

### Added

- Excel export columns for recovery audit fields:
  - `power_original`,
  - `power_recovered_from`,
  - `power_recovery_method`,
  - `power_recovery_status`,
  - `power_sanity_status`,
  - `power_sanity_confidence`,
  - `power_candidate_count`,
  - `power_candidate_best`,
  - `power_candidate_best_score`,
  - `power_candidate_second`,
  - `power_candidate_second_score`,
  - `power_candidate_margin`,
  - `power_recovery_selected_reason`,
  - `power_recovery_candidates`.
- Top-level `power_recovery` section in the import report.
- Per-row candidate traces in the import report.
- Per-import recovery counters.
- Regression coverage for Server 553-style reportability.

### Fixed

- Global `review_count` now aggregates import-level review counts instead of only counting concrete review objects.
- Candidate rows now carry direct best/second/margin fields, not only nested candidate metadata.

---

## Current known problems

### 1. Candidate scoring is explainable but still heuristic

**Status:** Improved, still needs operational validation  
**Observed on:** Server 553 regression class  
**Confidence:** High

Sentinel now exposes why a power candidate was selected or quarantined. The scoring engine is still heuristic and must continue to prefer quarantine when the best candidate is not clearly stronger than the second-best candidate.

### 2. Import session integrity remains open

**Status:** Open  
**Next Sprint:** v0.9.5.50

Sentinel still needs explicit import sessions and ranking segment metadata so mixed, missing, duplicate, and out-of-order screenshot sets can be detected without trusting filenames or upload order.

---

## Immediate next sprint recommendation: v0.9.5.50

### Focus

**Import Session and Segment Integrity**

### Expected outputs

- Explicit import session identifiers.
- Ranking segment metadata per source.
- Missing, duplicate, mixed, and out-of-order segment detection.
- Import report fields for segment continuity.
- Guardrails that continue to avoid filename/order/upload-order truth.

---

## Validation

```bash
python -m compileall -q parser services main.py version.py
pytest tests/smoke/test_ranking_power_sanity_guard.py tests/smoke/test_operational_import_repository.py tests/smoke/test_sentinel_ranking_guard.py tests/smoke/test_ranking_recovery.py -q
```

Observed result:

```text
23 passed
```

## v0.9.5.52 sprint result

v0.9.5.52 keeps the candidate recovery architecture from .51 but shifts the active risk control from pure power scoring to segment integrity. The patch adds a segment-order tie-breaker for close high-explosion THP candidates and tightens low-truncation recovery so ambiguous `scale_x10`/`insert_zero` candidates are quarantined instead of forced into Operational Truth.

The strategic takeaway from Server 549–553 remains: Power recovery is now explainable and safe enough to continue, but the next quality gains require better screenshot segment reconstruction, not broader heuristic recovery.

