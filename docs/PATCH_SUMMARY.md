# Patch Summary

## v0.9.5.150

### Strike VII — Position-Bound Evidence Provenance

This sprint extends v0.9.5.149 from position status to a full processing-chain diagnosis. For every non-confirmed character position Sentinel records the available screenshot and crop provenance, OCR output, vote state, reconstruction result, Promotion Guard consequence, the first failed stage, and the next evidence action.

New artifacts:

- `evidence_provenance_report.json`
- `evidence_provenance_report.xlsx`
- `evidence_provenance_summary.md`

Safety boundaries:

- no policy relaxation;
- no automatic clearance;
- no Ground Truth character acquisition;
- no UNKNOWN completion;
- no Operational Truth modification.


## Purpose

Convert the aggregate `name_exact` blocker into an explainable, position-bound evidence diagnosis. The release does not clear cases; it identifies exactly which character positions lack proof, contain unresolved votes, or carry conflicting screenshot evidence.

## Runtime changes

- New `_build_gold_core_character_evidence_map()` read-only report layer.
- Per-case evidence coverage and blocking-position inventory.
- Per-position evidence chain with crop and screenshot provenance.
- Cross-case position heatmap for prioritizing targeted evidence acquisition.

## Outputs

- `character_position_report.json`
- `character_position_report.xlsx`
- `character_position_summary.md`
- `position_heatmap.json`

## Safety

- Ground Truth remains comparison-only and is never used to fill missing characters.
- UNKNOWN remains uncompleted.
- Conflicting evidence remains blocking.
- Promotion and elimination policies are unchanged.
- Operational Truth remains unchanged.

---

# Patch Summary — v0.9.5.148

Documentation-only release based on Sentinel v0.9.5.147 and its Server 551 benchmark. Adds `BENCHMARK_ANALYSIS_v0.9.5.147.md` and aligns all strategic documentation with measured results. No production code, validation policy, OCR output, snapshot, Ground Truth, or Operational Truth is modified.

---

# v0.9.5.142 – Gold Core Strike III

## Functional changes

- Adds a conservative Strike III validator gate for one or two Latin substitutions that belong exclusively to known OCR glyph-confusion families.
- Requires accepted same-snapshot identity matching, exact power anchor, proven Core Alliance, Promotion Guard eligibility, zero unresolved fragments, zero observed votes, and confirmed character evidence for every changed position.
- Blocks identity guessing, arbitrary fuzzy substitutions, insertion/deletion shapes, context-gap inference and unstable Character Position Intelligence states.
- Preserves Operational Truth, Ground Truth, snapshots and exports unchanged.
- Adds dedicated Strike III smoke regressions while retaining Strike I/II coverage.

## Validation

- Targeted Gold-Core regression suite: 12 passed.
- The legacy full smoke suite is not clean in the supplied .141 baseline because it contains two shell-command files saved as Python tests and obsolete OCR configuration imports. These pre-existing collection defects were not masked or rewritten in this sprint.

# v0.9.5.141 – Character Position Intelligence Phase I

- Implements functional Character Position Intelligence in the validator, not just report scaffolding.
- Adds `character_position_intelligence_report.json/xlsx` with position-level risk, action, and rank-level acquisition focus.
- Feeds weak/critical position decisions into the Evidence Scheduler so Gold Accuracy prioritizes problematic character positions.
- Keeps Display Reconstruction, Strike clearance, Context Gaps, and Operational Truth read-only.
- Report phase label: `v0.9.5.141_character_position_intelligence`.

# v0.9.5.140 – Gold Regression & Strike II

- Adds permanent GC-001 Joncollins21 Gold-Core regression metadata.
- Extends Gold-Core elimination with Strike II: one missing Latin glyph plus optional known local glyph confusion, only when Rank/Power/Core Alliance anchors are proven.
- Keeps context gaps read-only and never modifies Operational Truth.
- Report phase label: `v0.9.5.140_gold_regression_strike_ii`.

## v0.9.5.140 – Gold Blocker Strike I

This release turns Gold-Core elimination from classification into a first targeted strike. It adds a narrow validator-side clearance path for localized Latin single-glyph blockers when every other identity anchor is already proven: non-context row, power match, core alliance proof, promotion eligibility, non-blocked evidence confidence, and one-character Latin display drift. Operational Truth remains unchanged; the clearance only affects benchmark evidence status and is fully reported.

Key changes:
- Added `clear_gold_core_blocker_strike_i` action.
- Added single-glyph Latin blocker clearance guard.
- Updated Gold-Core elimination phase labels to `v0.9.5.140_gold_blocker_strike_i`.
- Preserved context-gap read-only policy and DataGuard protections.

# Patch Summary

## v0.9.5.140 – Gold Core Elimination Phase I

### Purpose

v0.9.5.140 adds an evidence-only Character Acquisition Engine. The sprint shifts the Gold Accuracy line from additional guards toward better character evidence acquisition: multiple Character ReOCR observations are grouped by field and position, scored, and converted into consensus diagnostics.

### Implemented

- Added `character_acquisition_report.json` and `character_acquisition_report.xlsx`.
- Added per-observation confidence using OCR confidence, vote consensus, crop quality and target status.
- Added per-character consensus rows keyed by server, rank, field and position.
- Added acquisition heatmap for weak recurring character positions.
- Attached acquisition counts and average confidence to validation detail rows.
- Kept Character Acquisition strictly evidence-only; Operational Truth is not modified.

### Validation

- New Character Acquisition smoke tests pass.
- Existing display reconstruction, guard and budget smoke tests remain green.
- `py_compile` passes for `ground_truth_validator.py`.


## v0.9.5.129 – Read-only Verification Execution

### Purpose

Execute the read-only evidence lane that v0.9.5.128 only made eligible. Context Gap rows with strong structural evidence now receive report-only verification output. This is not an Operational Truth resolver and it does not write into exports, snapshots, database state, or Ground Truth.

### Implemented

- Added `read_only_reocr_executed`.
- Added `read_only_reocr_evidence` as an evidence-only JSON payload.
- Added `read_only_suggested_display`.
- Added `read_only_confidence`.
- Added `read_only_operational_truth_modified` and keeps it `false`.
- Upgraded eligible Context Gap rows from `eligible_not_executed_phase1` to `executed_evidence_only_phase2`.
- Updated `alignment_intelligence_report.json/xlsx` with execution fields.
- Added smoke test coverage for read-only evidence execution without truth promotion.

### Guardrails

- No Operational Truth mutation.
- No verified-display promotion from Context Gap evidence.
- No snapshot/export/database mutation.
- No rank/power/alliance-only player continuity promotion.
- Context Gap evidence remains report-only until a later explicit policy decides how to consume it.

### Validation

```bash
pytest -q tests/smoke/test_alignment_intelligence_128.py tests/smoke/test_read_only_verification_129.py
python -m py_compile ground_truth_validator.py
```

### Commit

```bash
git add .
git commit -m "feat(alignment): execute read-only verification evidence for v0.9.5.129"
git tag -a v0.9.5.129 -m "v0.9.5.129 Read-only Verification Execution"
```

## v0.9.5.128 – Alignment Intelligence Phase I

### Purpose

Introduce a first Alignment Intelligence layer for Context Gap rows. The sprint keeps DataGuard and Operational Truth locked, but records when a contextual row has enough structural evidence to allow future read-only character evidence work. This is not an OCR tuning sprint and it does not promote contextual inference into truth.

### Implemented

- Added per-row `alignment_score`.
- Added `alignment_score_evidence`.
- Added `verification_allowed_read_only`.
- Added `verification_block_reason`.
- Added `read_only_verification_status`.
- Added standalone `alignment_intelligence_report.json`.
- Added standalone `alignment_intelligence_report.xlsx`.
- Embedded Alignment Intelligence summary and rows in `ground_truth_validation_report.json`.
- Added `alignment_intelligence` and `alignment_intel_rows` workbook sheets.
- Added smoke tests for high-confidence Context Gap read-only eligibility and normal observed-row policy preservation.

### Guardrails

- Operational Truth remains unchanged.
- Context Gap verification is evidence-only.
- No snapshot/export/database mutation.
- No rank/power/alliance continuity promotion.
- No Character ReOCR execution on Context Gaps in Phase I; `.128` only introduces the safe scoring and report gate.

### Validation

```bash
pytest -q tests/smoke/test_alignment_intelligence_128.py tests/smoke/test_gold_core_resolution_plan_127.py tests/smoke/test_gold_core_blocker_report_126.py
python -m py_compile ground_truth_validator.py
```

### Commit

```bash
git add .
git commit -m "feat(alignment): add read-only alignment intelligence for v0.9.5.128"
git tag -a v0.9.5.128 -m "v0.9.5.128 Alignment Intelligence Phase I"
```

## v0.9.5.127 – Gold Core Resolution Plan

### Purpose

Convert the v0.9.5.126 Gold Core blocker triage into an executable, guardrail-safe resolution plan. This sprint does not weaken DataGuard, Ranking Guard, Alignment Guard, or Operational Truth. It adds a dedicated planning layer that tells Sentinel which blockers are safe local automation candidates and which must remain blocked by crop geometry, script policy, observed evidence, or manual review.

### Implemented

- Added `gold_core_resolution_plan_report.json`.
- Added `gold_core_resolution_plan_report.xlsx`.
- Embedded `gold_core_resolution_summary` and `gold_core_resolution_plan` into `ground_truth_validation_report.json`.
- Added `gold_core_plan` and `gold_core_plan_rows` sheets to the validation workbook.
- Added `_classify_gold_core_resolution_action(...)` and `_build_gold_core_resolution_plan_report(...)`.
- Added smoke tests for safe warning downgrade, crop-geometry stop signs, and nonlocal script policy blocking.

### Guardrails

- No Operational Truth mutation.
- No Character ReOCR on context gaps.
- No historical identity memory.
- No rank/power/alliance-only player continuity promotion.
- Vote-warning downgrade is only a candidate path when expected-only glyph evidence is clean and Core Identity is already proven.

### Validation

```bash
pytest -q tests/smoke/test_gold_core_resolution_plan_127.py tests/smoke/test_gold_core_blocker_report_126.py
python -m py_compile ground_truth_validator.py
```

### Commit

```bash
git add .
git commit -m "feat(gold-core): add resolution plan report for v0.9.5.127"
git tag -a v0.9.5.127 -m "v0.9.5.127 Gold Core Resolution Plan"
```

## v0.9.5.126 – Gold Core Blocker Triage

### Purpose

Turn the remaining Gold Core blockers into an explicit operational triage report. The sprint is intentionally diagnostic: it classifies blockers and proposes safe fix lanes without changing matching, inference, ReOCR voting, DataGuard, Ranking Guard, or Operational Truth.

### Code Changes

- Added `_classify_gold_core_blocker(...)`.
- Added `_build_gold_core_blocker_report(...)`.
- Merged Gold Blocker Triage with OCR Evidence Inspector row statuses.
- Wrote standalone `gold_core_blocker_report.json/xlsx`.
- Embedded Gold Core summary/detail sections into the existing validation reports.

### Classification Lanes

- `local_glyph_solvable` – local Latin glyph/crop refinement candidate.
- `mixed_local_and_nonlocal_blocker` – local glyph work exists, but full display is still limited by script/nonlocal policy.
- `policy_nonlocal_script_display` – multilingual/nonlocal display cannot be safely repaired by local glyph logic.
- `crop_geometry_problem` – crop anchor or field/power-column bleed must be fixed first.
- `observed_text_confirmed` – local evidence supports observed OCR text, so expected display stays blocked.
- `vote_warning_gate_review` – potential warning downgrade candidate only if selected expected glyph and Core Identity are otherwise proven.
- `context_gap_read_only` – alignment/context issue; not a Character ReOCR problem.
- `manual_review` – unexpected signature requiring manual inspection.

### Safety

No Operational Truth mutation. No historical player-memory shortcut. No pre/post transfer identity inference. No Character ReOCR on context gaps.

### Validation

```text
pytest -q tests/smoke/test_gold_core_blocker_report_126.py tests/smoke/test_gold_blocker_triage_113.py tests/smoke/test_gold_gate_cleanup_114.py
6 passed
python3 -m py_compile ground_truth_validator.py
OK
```

### Commit / Tag

```bash
git add .
git commit -m "feat(gold-core): add blocker triage report for v0.9.5.126"
git tag -a v0.9.5.126 -m "v0.9.5.126 Gold Core Blocker Triage"
```

---


## v0.9.5.125 – Documentation Consolidation & Handover

### Purpose

Create a clean, deployable documentation release after the v0.9.5.124 Gold Fidelity Engine Phase 1 sprint. The goal is handover stability: the next chat should understand the project state, the operating rules, the DataGuard principles, the latest validation results, and the path to v1.0.0 without relying on hidden chat context.

### Scope

- Documentation-only sprint.
- No intentional changes to OCR, parsing, matching, DataGuard, Ranking Guard, Character ReOCR, Evidence Cache, inference, exports, or Operational Truth.
- Version raised to `0.9.5.125` for release traceability.

### Updated / Added Documentation

- `docs/RELEASE_NOTES.md`
- `docs/PATCH_SUMMARY.md`
- `docs/PROJECT_STATUS.md`
- `docs/ROAD_TO_V1.md`
- `docs/LESSONS_LEARNED.md`
- `docs/MODUS_OPERANDI.md`
- `docs/SENTINEL_DATA_GUARD.md`
- `docs/ARCHITECTURE.md`
- `docs/ARCHITECTURAL_DECISIONS.md`
- `docs/NEXT_CHAT.md`
- `docs/HANDOFF_NEXT_CHAT.md`
- `docs/ARCHITECTURE_HISTORY.md`
- `docs/VERSIONING_POLICY.md`
- `docs/RELEASE_NOTED.md`

### Current Technical Baseline Captured

- Latest source baseline: `Sentinel_v0.9.5.124.zip`.
- Latest functional milestone: Gold Fidelity Engine Phase 1.
- Latest benchmark focus: server 551 total hero power ground truth validation.
- Observed v0.9.5.124 result:
  - 50/50 matched rows;
  - 0 missing rows;
  - 0 bad matches;
  - 100% recall;
  - 32 verified core identity matches;
  - 15 remaining Gold Core blockers;
  - row integrity score 66%;
  - validator runtime about 480 seconds on the reported CPU-only run;
  - ReOCR evidence cache: 11 hits, 53 misses, 41 writes, 11 saved ReOCR calls.

### Commit / Tag

```bash
git add .
git commit -m "docs(project): consolidate handover documentation for v0.9.5.125"
git tag -a v0.9.5.125 -m "v0.9.5.125 Documentation Consolidation and Handover"
```


# Consolidated Historical Patch Summaries

# Patch Summary – v0.9.5.124 Gold Fidelity Engine Phase 1

## Purpose

This sprint starts the Gold Fidelity Engine by reusing screenshot-local evidence instead of repeatedly invoking CPU-heavy Character ReOCR for identical glyph claims inside one validation run. It preserves Data Guard: cached evidence is provenance-marked and never changes Operational Truth.

## Changes

- Added conservative snapshot-local ReOCR evidence cache.
- Added exact cache keys by target field, position, expected/observed glyph, reason, expected text, and observed text.
- Cached only decisive `verified_expected` / `verified_observed` outcomes.
- Cloned cache hits as `CharacterVerificationEvidence` with `reason=evidence_cache_hit`, `crop_strategy=snapshot_evidence_cache`, zero timing, and no crop box/votes.
- Added validator detail telemetry columns:
  - `reocr_evidence_cache_hits`
  - `reocr_evidence_cache_misses`
  - `reocr_evidence_cache_writes`
  - `reocr_evidence_cache_saved_reocr`
- Added focused smoke tests for cache behavior.

## Validation

```text
focused smoke tests passed
py_compile OK
zip integrity OK
```

## Commit

```bash
git add .
git commit -m "perf(gold-fidelity): cache reusable reocr evidence"
git tag -a v0.9.5.124 -m "v0.9.5.124 Gold Fidelity Engine Phase 1"
```

---

<!-- Consolidated from PATCH_SUMMARY_0.9.5.123.md -->

# v0.9.5.123
Planned changes:
- Evidence triage strategy
- ReOCR stop rules
- Budget gate refinements
This package is a planning placeholder built from v0.9.5.122.


---

<!-- Consolidated from PATCH_SUMMARY_0.9.5.124.md -->

# Patch Summary – v0.9.5.124 Gold Fidelity Engine Phase 1

## Purpose

This sprint starts the Gold Fidelity Engine by reusing screenshot-local evidence instead of repeatedly invoking CPU-heavy Character ReOCR for identical glyph claims inside one validation run. It preserves Data Guard: cached evidence is provenance-marked and never changes Operational Truth.

## Changes

- Added conservative snapshot-local ReOCR evidence cache.
- Added exact cache keys by target field, position, expected/observed glyph, reason, expected text, and observed text.
- Cached only decisive `verified_expected` / `verified_observed` outcomes.
- Cloned cache hits as `CharacterVerificationEvidence` with `reason=evidence_cache_hit`, `crop_strategy=snapshot_evidence_cache`, zero timing, and no crop box/votes.
- Added validator detail telemetry columns:
  - `reocr_evidence_cache_hits`
  - `reocr_evidence_cache_misses`
  - `reocr_evidence_cache_writes`
  - `reocr_evidence_cache_saved_reocr`
- Added focused smoke tests for cache behavior.

## Validation

```text
focused smoke tests passed
py_compile OK
zip integrity OK
```

## Commit

```bash
git add .
git commit -m "perf(gold-fidelity): cache reusable reocr evidence"
git tag -a v0.9.5.124 -m "v0.9.5.124 Gold Fidelity Engine Phase 1"
```


## v0.9.5.130
- Documentation sprint.
- Captured analysis of validation results.
- Defined Display Reconstruction Engine as next engineering milestone.


## v0.9.5.131

### Display Reconstruction Engine Phase I

This sprint turns the previous `.130` roadmap into the first functional evidence-consumption layer. Sentinel now produces a dedicated Display Reconstruction report from already collected Character ReOCR evidence and read-only context-gap evidence.

### Added

- `_apply_display_reconstruction()` in `ground_truth_validator.py`.
- `_build_display_reconstruction_report()` for standalone JSON/XLSX output.
- Report-only reconstruction columns on validation detail rows.
- `display_reconstruction_report.json/xlsx`.
- Smoke test: `tests/smoke/test_display_reconstruction_131.py`.

### Guardrails

- Operational Truth remains locked.
- `verified_name_display` and `verified_alliance_display` are not overwritten.
- Context-gap suggestions remain `read_only_contextual_inference`.
- Observed-vote conflicts are surfaced instead of silently corrected.

### Commit

```bash
git add .
git commit -m "feat(display): add read-only display reconstruction report"
git tag -a v0.9.5.131 -m "v0.9.5.131 Display Reconstruction Engine Phase I"
```

## v0.9.5.132

### Display Reconstruction Guard

This sprint adds the safety layer required after `.131`: Display Reconstruction may still collect and expose evidence, but unsafe name promotion is blocked before a synthesized display string is surfaced.

### Added

- Display promotion guard in `ground_truth_validator.py`.
- New report fields:
  - `display_promotion_eligible`
  - `display_promotion_block_reason`
- New guarded statuses:
  - `alliance_reconstructed_name_blocked`
  - `blocked_display_promotion`
- Smoke test: `tests/smoke/test_display_reconstruction_guard_132.py`.

### Guardrails

- Blocks name reconstruction from `UNKNOWN` bases.
- Blocks low-coverage name reconstruction when the reconstructed name does not match expected display.
- Blocks name promotion when observed-vote conflicts or unresolved fragments remain.
- Allows safe alliance reconstruction to remain visible even when name promotion is blocked.
- Operational Truth remains unchanged.

### Commit

```bash
git add .
git commit -m "feat(display): add reconstruction promotion guard"
git tag -a v0.9.5.132 -m "v0.9.5.132 Display Reconstruction Guard"
```

## v0.9.5.133

Sprint: **Evidence Confidence Engine**

This patch adds a read-only confidence layer on top of Display Reconstruction.

Implemented:
- `evidence_confidence_report.json/xlsx`
- `evidence_avg_fragment_confidence`
- `display_name_coverage_score`
- `display_alliance_coverage_score`
- `display_coverage_score`
- `display_confidence_decision`
- fragment confidence components for crop/OCR/vote/position/script/status

Safety:
- no Operational Truth changes
- no export mutation
- no snapshot mutation
- no Ground Truth mutation
- context-gap display remains suggestion-only

Validation target:
```bash
pytest tests/smoke -q
python -m py_compile ground_truth_validator.py
```

Commit:
```bash
git add .
git commit -m "feat(evidence): add display evidence confidence scoring"
git tag -a v0.9.5.133 -m "v0.9.5.133 Evidence Confidence Engine"
```


## v0.9.5.134 – Evidence Budget Manager

This release adds a read-only Evidence Budget Manager for Display Fidelity. The new budget layer scores display reconstruction candidates before future expensive ReOCR work is promoted into the active pipeline. It introduces `evidence_priority_score`, `evidence_budget_tier`, `evidence_budget_action`, `evidence_budget_reason`, and the standalone `evidence_budget_report.json/xlsx`.

The sprint does not change Operational Truth, snapshots, exports, Ground Truth, or DataGuard policy. Its purpose is to make future Character ReOCR investment explainable and selective: high-value candidates can receive full budget, medium candidates receive targeted budget, weak evidence is blocked early or served from cache.


## v0.9.5.135 – Evidence Scheduler Phase I

### Purpose
Turn the passive Evidence Budget Manager into a report-only scheduler plan that can later control Character ReOCR runtime safely.

### Added
- `_scheduler_priority_from_budget`
- `_attach_evidence_scheduler`
- `_build_evidence_scheduler_report`
- `evidence_scheduler_report.json/xlsx`
- smoke tests for scheduler early exit, full scheduling, and report summary

### Safety
The scheduler is Phase I/report-only. It does not alter OCR rows, exports, snapshots, Ground Truth, or Operational Truth.

## v0.9.5.136 – Gold Accuracy Mode

- Added functional `GOLD_ACCURACY_MODE = True`.
- Disabled runtime-first local glyph budget skips in `_apply_reocr_budget_gate`.
- Reworked Evidence Scheduler into an accuracy orchestrator.
- Replaced low-priority `early_exit_cache_only` behavior with `schedule_accuracy_reocr`.
- Preserved read-only contextual inference and Operational Truth protection.
- Added Gold Accuracy Mode smoke tests.

## v0.9.5.143

Gold Core Strike IV turns remaining blockers into explainable quality intelligence. Each candidate is assigned a root-cause class, confidence, priority and recommended next action. A persistent failure memory tracks recurrence and resolution across validator runs. No OCR export, snapshot, Ground Truth or Operational Truth is modified.

## v0.9.5.144 – Gold Core Strike V

Gold Core knowledge is consolidated into one consistent case model. Existing validator
triage is authoritative; analytics heuristics are fallback-only. The validator now emits
a case explorer, prioritized action list, generated casebook, enriched analytics workbook,
and Failure Memory 2.0. All artifacts are read-only and cross-linked through stable
server/rank case IDs.

Validation target:

```cmd
pytest -q tests\smoke\test_gold_core_strike_v_144.py tests\smoke\test_gold_core_strike_iv_143.py tests\smoke\test_gold_core_strike_iii_142.py tests\smoke\test_gold_core_strike_140.py tests\smoke\test_gold_blocker_strike_139.py tests\smoke\test_character_position_intelligence_141.py
python -m py_compile ground_truth_validator.py gold_core\quality_intelligence.py
```

## v0.9.5.145 — Gold Core Zero I

### Objective
Begin measurable Gold Core elimination by resolving warning-only vote noise without weakening evidence standards.

### Implementation
- `_gold_core_vote_policy_clearance()` parses current-snapshot character evidence.
- Expected-only consensus may clear only with exact player-name proof, alliance proof, power proof, accepted matching, and zero counterevidence.
- Crop mismatch, observed evidence, unresolved/ambiguous votes, context gaps, missing identity anchors, or non-accepted matches remain hard blockers.
- Elimination attribution is explicit as `clear_gold_core_blocker_vote_policy`.
- Operational Truth is read-only.


## v0.9.5.146 — Gold Core Zero II

### Objective
Make the Promotion Guard explainable and remove only proven low-coverage false negatives.

### Implementation
- `_promotion_guard_diagnostics()` emits the complete guard truth table for every candidate.
- `_gold_core_promotion_guard_clearance()` applies a class-bound, evidence-bound override.
- New elimination attribution: `clear_gold_core_blocker_promotion_guard_rationalized`.
- Gold Core elimination reports now expose the exact failed conditions instead of only the legacy aggregate reason.

### Guardrails
- Override is restricted to `vote_warning_gate_review`.
- A legacy `blocked_low_coverage` or budget reason is required.
- Expected-only screenshot evidence, exact name, alliance, power, and accepted matching are mandatory.
- Any context gap, observed counterevidence, unresolved vote, crop mismatch, or different failure class remains blocked.
- Operational Truth is never modified.

## v0.9.5.147 — Gold Core Zero III

Implemented complete evidence-bound name reconstruction with position coverage, conflict and missing-position diagnostics, a new conservative clearance path, Failure Memory metadata, regression tests, and full report integration.
