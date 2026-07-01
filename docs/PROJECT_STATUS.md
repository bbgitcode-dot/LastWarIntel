# Sentinel Project Status

**Current Version:** v0.9.5.48  
**Sprint Type:** Data Integrity / Recovery Reportability  
**Runtime Baseline:** v0.9.5.48 – Source Context Recovery Reportability  
**Current Phase:** Data Integrity Fortress / Operational Data Stability  
**Next Planned Sprint:** v0.9.5.49 – Import Session and Segment Integrity

---

## Executive summary

Sentinel v0.9.5.48 makes context-aware power recovery explainable in the operational outputs that leadership and review workflows actually consume.

v0.9.5.47 introduced the candidate-scoring engine. v0.9.5.48 exposes its evidence in the Excel export and in `data/latest_import_report.json`: original value, selected value, candidate list, best/second score, score margin, confidence, method, and decision reason.

The sprint also fixes a report integrity problem observed in the Server 553 run: the global report could show `review_count: 0` while import blocks still showed review counts. Global review aggregation now reflects import-level review warnings, while `review_item_count` remains available for concrete quarantine/data-guard review objects.

---

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
**Next Sprint:** v0.9.5.49

Sentinel still needs explicit import sessions and ranking segment metadata so mixed, missing, duplicate, and out-of-order screenshot sets can be detected without trusting filenames or upload order.

---

## Immediate next sprint recommendation: v0.9.5.49

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
