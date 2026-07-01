# Sentinel Project Status

**Current Version:** v0.9.5.47  
**Sprint Type:** Data Integrity / Recovery Hardening  
**Runtime Baseline:** v0.9.5.47 – Context-aware Power Candidate Recovery  
**Current Phase:** Data Integrity Fortress / Operational Data Stability  
**Next Planned Sprint:** v0.9.5.48 – Import Session and Segment Integrity

---

## Executive summary

Sentinel v0.9.5.47 replaces the narrow single-candidate leading-digit recovery path with a context-aware power candidate recovery engine.

The old v0.9.5.45 behavior could detect obvious `7xxM` Total Hero Power and `77B` Alliance Power OCR explosions, but it could still choose the wrong corrected value because it only tried the deterministic leading-digit replacement. Server 553 proved that `764M` may not always mean `164M`; in some contexts the better candidate is closer to `224M`.

v0.9.5.47 now generates several candidate values, scores them with source-local context, and recovers only when one candidate is clearly strongest. Ambiguous cases remain guarded through quarantine or legacy-safe fallback only where the earlier deterministic evidence path is still explicitly covered by regression tests.

---

## What changed in v0.9.5.47

### Added

- `PowerRecoveryCandidate` model for scored recovery candidates.
- Context-aware candidate generation for suspicious THP and Alliance Power values.
- Candidate scoring using:
  - source-local low power envelope,
  - OCR rank context where available,
  - visual source row position,
  - prior and following neighbour powers,
  - monotonic rank-order fit,
  - local bucket match,
  - ranking type.
- Recovery metadata on recovered rows:
  - `power_recovery_candidates`,
  - `power_recovery_selected_score`,
  - `power_recovery_selected_reason`,
  - `power_recovery_method=<ranking_type>_context_candidate_recovery`.
- Ambiguous candidate metadata on quarantined rows.
- Regression tests for Server 553-style context recovery, including `764M -> 224M` and Alliance Power candidate selection.

### Preserved

- Data Guard doctrine: no filename/order/upload-order truth.
- Ranking Guard semantic boundaries.
- Power Sanity Guard protection against false `7xxM` / `77B` values.
- Legacy deterministic recovery behavior for already-covered safe cases.

---

## Current known problems

### 1. Candidate scoring is now present but still heuristic

**Status:** Improved, still needs operational validation  
**Observed on:** Server 553 regression class  
**Confidence:** High

The engine now scores multiple candidates and can select a non-legacy candidate such as `224M` when the local rank context is clear. However, final correctness still depends on OCR row quality and source-local neighbour evidence. Ambiguous values must remain reviewable.

### 2. Import session integrity remains open

**Status:** Open  
**Next Sprint:** v0.9.5.48

Sentinel still needs explicit import sessions and ranking segment metadata so mixed, missing, duplicate, and out-of-order screenshot sets can be detected without trusting filenames or upload order.

---

## Immediate next sprint recommendation: v0.9.5.48

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
python -m compileall -q parser main.py version.py
pytest tests/smoke/test_ranking_power_sanity_guard.py tests/smoke/test_thp_power_sanity_guard.py tests/smoke/test_sentinel_ranking_guard.py tests/smoke/test_ranking_recovery.py -q
```

Observed result:

```text
24 passed
```
