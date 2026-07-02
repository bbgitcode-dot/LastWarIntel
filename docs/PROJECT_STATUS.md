## v0.9.5.59 Status – Review UX & Explainability Foundation

Current focus has shifted from improving OCR heuristics to improving review trust and explainability.

### Current State

- Data Guard and Ranking Guard continue to protect Operational Truth.
- Review Evidence Pack is now backed by human-readable problem statements and candidate choices.
- Review Center is introduced as the integrated review workspace.
- Review History is becoming the persistent foundation for future manual resolution.

### Next Step

v0.9.5.60 should implement the first read/write review resolution model: accepting a candidate, entering a manual value, saving a comment, and marking the review as resolved without mutating raw OCR evidence.

**Current Version:** v0.9.5.58  
**Runtime Baseline:** v0.9.5.58 – Human Review Guidance

## v0.9.5.58 sprint result

The Review Evidence Pack now explicitly tells the human reviewer what is uncertain: power value, alliance power outlier, server assignment, row/rank ambiguity, name ambiguity, or generic manual review. Candidate choices are exposed as review options, not Operational Truth.

A persistent review history foundation was added via `data/review_history.json`, mirrored to `output/review_history.json`. This prepares Sentinel for future multi-source screenshot ingestion and resolved-review workflows without bypassing Data Guard.

## Next recommended sprint

`v0.9.5.59 – Review Resolution Model`: add review states (`OPEN`, `IN_REVIEW`, `RESOLVED`, `DISMISSED`) and manual override/audit structures.

**Current Version:** v0.9.5.57  
**Runtime Baseline:** v0.9.5.57 – Evidence Trace Binding  
**Sprint Focus:** Make Review Evidence Pack cards explain candidate decisions instead of showing empty trace fields.

## v0.9.5.57 sprint result

v0.9.5.56 created `review_evidence_pack.html` and `.json`, but targeted 554 review showed that some cards lacked `power_original`, best/second candidate, margin, and trace data. The issue was not missing recovery data; it was that review rows often represent expected ranking types while their detailed candidate traces are emitted under `ranking_guard_quarantine`.

v0.9.5.57 adds conservative Evidence Trace Binding. Review cards first try exact trace matching, then screenshot-local fallback using rank, expected ranking type, `best=` and `margin=` hints from the review description. This keeps the Evidence Pack read-only while making review decisions understandable.

The Command Center remains a run overview; the Evidence Pack becomes the detail surface. A later sprint should integrate this detail surface into the broader Command Center click path instead of treating it as a loose output file.

Next likely sprint: Review crop assets / visual row evidence, or Manual Review Resolution Model once the evidence is complete enough.

**Current Version:** v0.9.5.56  
**Runtime Baseline:** v0.9.5.56 – Review Evidence Pack  
**Sprint Focus:** Make review items actionable without expanding the Command Center into another noisy dashboard.

## v0.9.5.56 sprint result

v0.9.5.55 introduced the Command Center MVP and confirmed that Sentinel can render run status after every import. The follow-up run also showed that a broad dashboard can become too much input when the real need is to understand one specific review item.

v0.9.5.56 therefore adds a focused Review Evidence Pack. After each run Sentinel now emits `output/review_evidence_pack.html` and `output/review_evidence_pack.json`. Each evidence card summarizes the exact review item, its screenshot reference, candidate power evidence, best/second candidate gap, decision reason, review OCR status, row reconstruction status, and suggested human action.

The Command Center remains useful as an operations overview, but the Evidence Pack becomes the primary surface for review quality work. OCR, Recovery, Data Guard, Ranking Guard, and export logic remain unchanged.

Next likely sprint: Review crop assets and visual crop linking for each evidence card.

**Current Version:** v0.9.5.55  
**Runtime Baseline:** v0.9.5.55 – Command Center MVP  
**Sprint Focus:** Make run outcomes visible through static dashboards generated from existing reports.

## v0.9.5.55 sprint result

v0.9.5.55 adds the first operational Command Center. After `main.py` writes the import report, Sentinel now generates `output/command_center.html` and `output/review_dashboard.html`. The dashboards summarize readiness, Data Guard status, server/ranking groups, power recovery traces, review items, and ground-truth metrics.

This sprint intentionally leaves OCR, Recovery, Data Guard, Ranking Guard, and Row Reconstruction untouched. The dashboards are report-driven views only. This preserves report artifacts as the single source of truth while making the result of a long import run understandable in seconds.

Next likely sprint: Review Center with crop/image evidence and richer manual review ergonomics.

**Current Version:** v0.9.5.54  
**Runtime Baseline:** v0.9.5.54 – Contextual Row Reconstruction  
**Sprint Focus:** Review rows can now be promoted only when source-local anchor rows bound a safe reconstructed row.

## v0.9.5.54 sprint result

v0.9.5.53 proved that enhanced Review OCR is technically useful infrastructure but did not promote any of the 12 review rows from the 549–553 regression run. The remaining failures are no longer pure image-filter problems; they are bounded row/rank reconstruction problems.

v0.9.5.54 adds a conservative Contextual Row Reconstruction stage after adaptive Review OCR. For low/truncated THP rows, Sentinel now checks whether a digit-preserving recovered candidate fits between trusted source-local anchor powers from the same screenshot. Promotion requires:

- same source screenshot,
- same server and ranking type,
- at least two trusted source-local anchor rows,
- a normal THP candidate,
- strong digit preservation,
- bounded anchor order consistency,
- no near-duplicate existing power.

If those conditions are not met, the row stays in quarantine. This preserves the rule: quarantine beats false Operational Truth.

**Current Version:** v0.9.5.53  
**Runtime Baseline:** v0.9.5.53 – Adaptive Review OCR Pipeline  
**Sprint Focus:** Review rows now receive a source-local second-pass OCR attempt before remaining in quarantine.

## v0.9.5.53 sprint result

The sprint adds the first adaptive Review OCR pipeline. v0.9.5.52 made Power Recovery safer through segment-order guardrails; .53 addresses the next bottleneck: review rows that are likely caused by crop/image/OCR quality rather than by power scoring alone.

The pipeline runs after Ranking Guard and Power Sanity Guard. It loads the original source screenshot, crops around the quarantined row's visual y-position, creates zoom/enhancement variants, reruns OCR, and promotes only clear second-pass rows. If evidence does not improve, the row remains quarantined with review OCR metadata.


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

## Current Status - v0.9.5.60

The Review UX foundation from v0.9.5.59 is now consolidated into the product navigation. The main operational issue discovered after v0.9.5.59 was review-history duplication: repeated runs of the same unresolved screenshots created additional OPEN reviews. v0.9.5.60 fixes this by introducing stable review identities and rerun-aware `last_seen_at` / `seen_count` tracking.

The web surface is being organized around a clearer information architecture: Command Center for overall state, Imports for sources/runs, Quality for guards and metrics, Reviews for human decisions, and Reports for generated artifacts.
