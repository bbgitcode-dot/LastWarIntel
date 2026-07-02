# Sentinel v0.9.5.61 – Interactive Review Resolution Foundation

Sentinel v0.9.5.61 introduces the first write-capable human-review workflow. The web Review Center can now mark persistent review-history items as `RESOLVED`, store the selected candidate or manual value, keep reviewer/comment metadata, and reopen resolved items when needed.

## Highlights

- Added web Review Center resolve actions for persistent reviews.
- Added candidate selection, manual value/name/alliance fields, reviewer, and comment capture.
- Added reopen support for resolved reviews.
- Kept resolution state in `data/review_history.json`; Operational Truth and Excel exports remain unchanged.
- Static output pages remain read-only run-detail views.

## Guardrails

Manual resolution is audit state only. It does not override OCR output, promote quarantined rows, or change Operational Truth. A future guarded Manual Override Engine must explicitly consume resolved reviews before export changes are allowed.

# Sentinel v0.9.5.59 – Review UX & Explainability Foundation

Sentinel v0.9.5.59 improves the human review workflow. Reviews now explain what is uncertain, why Sentinel refused automatic promotion, what candidates are available, and which decision a human needs to make.

## Highlights

- New integrated Review Center (`output/review_center.html`).
- Human-readable review problem statements.
- "Warum?" explainability notes for each review item.
- Decision-path trace from OCR through Data Guard and Human Review.
- Review History visualization prepared for future resolution workflows.
- Resolution template fields for selected candidate, manual value, reviewer, comment, and resolved timestamp.

## Guardrails

The sprint is intentionally UI/report-driven only. It does not change OCR, power recovery, ranking guard, Data Guard, or export behavior.

# Sentinel v0.9.5.58 – Human Review Guidance

This release turns the Review Evidence Pack from a technical trace viewer into a human review guide. Each review item now says what Sentinel could not determine, lists the strongest candidate choices, and always offers manual input as a safe path.

The sprint also introduces `data/review_history.json` as the first persistent foundation for historical reviews. Current runs remain read-only, but reviews no longer have to be treated as purely ephemeral output artifacts.

## Validation

- `pytest tests/smoke/test_command_center.py -q`
- `python -m compileall services/command_center.py main.py version.py`

# Sentinel v0.9.5.57 – Evidence Trace Binding

## Focus

Make the Review Evidence Pack explain *why* a row is in review. v0.9.5.56 created evidence cards, but some cards had empty candidate fields because the review row described the expected ranking while the recovery trace lived under `ranking_guard_quarantine`. v0.9.5.57 binds these together conservatively.

## Added

- Trace binding between review items and `power_recovery.traces`.
- Fallback matching by screenshot, rank, expected ranking type, best-score hint, and margin hint.
- Evidence-card fields for trace status, trace source, candidate count, digit-preservation score, and candidate reasons.
- Direct links from review tables to evidence-card anchors.

## Guardrails

- Evidence Trace Binding is read-only.
- Fallback trace matching is only used for display evidence.
- Operational Truth, quarantine state, and export rows are not changed.

## Validation

```text
pytest tests/smoke/test_command_center.py -q
2 passed
python -m compileall -q services/command_center.py main.py version.py
```

---

# Sentinel v0.9.5.56 – Review Evidence Pack

## Focus

Reduce review noise. v0.9.5.55 proved that broad dashboards are useful for observability but too noisy for deciding individual review items. v0.9.5.56 adds a focused evidence pack for human review.

## Added

- `output/review_evidence_pack.html` with one concise evidence card per review item.
- `output/review_evidence_pack.json` for machine-readable review evidence.
- Evidence fields for screenshot, server, ranking, rank, original/selected power, best/second candidate, margin, decision reason, Review OCR status, Row Reconstruction status, and suggested action.
- Candidate-detail expansion for ambiguous power recovery cases.
- Link from Command Center / Review Dashboard to the Evidence Pack.

## Guardrails

- Evidence Pack reads `data/latest_import_report.json` only.
- It is intentionally narrower than the Command Center.
- It does not duplicate OCR, recovery, Data Guard, or quarantine logic.
- It does not write manual review decisions back into Operational Truth.

## Validation

```text
pytest tests/smoke/test_command_center.py -q
1 passed
python -m compileall -q services/command_center.py main.py version.py
```

---


# Sentinel v0.9.5.55 – Command Center MVP

## Focus

Make every run visually reviewable without opening raw JSON or Excel first. This is an observability sprint, not an OCR-core sprint.

## Added

- `output/command_center.html` with run summary, readiness, server cards, recovery counters, review rows, power traces, ground-truth metrics, and artifact links.
- `output/review_dashboard.html` with the first table-oriented review surface for quarantine/review items.
- `services.command_center` as a static HTML renderer.
- Automatic dashboard generation at the end of `main.py`.
- Smoke test coverage for dashboard generation.

## Guardrails

- The dashboard reads existing reports only:
  - `data/latest_import_report.json`
  - `benchmarks/ground_truth_validation_report.json`
  - `benchmarks/inference_report.json`
- No OCR logic is duplicated.
- No manual review decision is written back to Operational Truth.
- No screenshot filename/order/upload order is treated as truth.

## Validation

```text
pytest tests/smoke/test_command_center.py -q
1 passed
python -m compileall -q services/command_center.py main.py version.py
```

---


---

# Sentinel v0.9.5.54 – Contextual Row Reconstruction

## Focus

Turn Review from passive quarantine into conservative source-local row reconstruction for bounded low-truncation THP gaps.

## Added

- Contextual Row Reconstruction after Adaptive Review OCR.
- Source-local anchor evaluation for quarantined low/truncated THP rows.
- Digit-preserving candidate promotion only when the candidate fits between trusted rows from the same screenshot.
- Export/report metadata:
  - `row_reconstruction_attempted`
  - `row_reconstruction_status`
  - `row_reconstruction_score`
  - `row_reconstruction_reason`
  - `row_reconstruction_anchor_before_power`
  - `row_reconstruction_anchor_after_power`
  - `row_reconstruction_rank`
  - `row_reconstruction_method`
  - `digit_preservation_score`

## Guardrails

- No filename order.
- No upload order.
- No cross-screenshot sequence truth.
- No promotion without bounded source-local anchors.
- Quarantine remains default when evidence is incomplete.

## Validation

```text
pytest tests/smoke/test_adaptive_review_ocr.py tests/smoke/test_ranking_power_sanity_guard.py tests/smoke/test_inference_context_engine.py tests/smoke/test_gap_recovery.py tests/smoke/test_ground_truth_validator.py -q
31 passed
python -m compileall -q parser services main.py version.py ground_truth_validator.py
```

## Commit

```bash
git add .
git commit -m "feat(review): add contextual row reconstruction"
git tag -a v0.9.5.54 -m "v0.9.5.54 Contextual Row Reconstruction"
```
**Current Version:** v0.9.5.53

## v0.9.5.53 – Adaptive Review OCR Pipeline

Adds a second-pass OCR stage for rows Sentinel already isolated for review/quarantine. Instead of immediately stopping at quarantine, Sentinel now attempts deterministic source-local row crops with zoom, CLAHE, sharpen, and multi-variant OCR. A row is promoted back into Operational Truth only when the enhanced OCR pass produces clearly better intrinsic evidence; otherwise it remains quarantined with explicit review OCR metadata.

### Added
- `parser/review_ocr.py` adaptive review OCR pipeline.
- Row-crop, tall-crop, shifted-crop, 2x zoom, CLAHE, and sharpen review variants.
- Conservative promotion gate for review OCR results.
- Export/report metadata: `review_ocr_attempted`, `review_ocr_status`, `review_ocr_variants`, `review_ocr_best_variant`, `review_ocr_score`, `review_ocr_decision`.
- Top-level `review_ocr` section in `data/latest_import_report.json`.
- Regression tests for review OCR variant generation, quarantine promotion, and report summaries.

### Guardrails
- Review OCR is source-local and row-local. It never uses filename order, upload order, or neighbouring screenshots as truth.
- Operational Truth is modified only when enhanced OCR improves the row evidence above a strict threshold.
- Failed or weak review OCR attempts remain quarantine, not inferred truth.

### Validation
```bash
pytest tests/smoke/test_adaptive_review_ocr.py tests/smoke/test_operational_import_repository.py tests/smoke/test_ranking_power_sanity_guard.py -q
# 23 passed
```

### Commit
```bash
git add .
git commit -m "feat(review): add adaptive review OCR pipeline"
git tag -a v0.9.5.53 -m "v0.9.5.53 Adaptive Review OCR Pipeline"
```

# Sentinel Release Notes

**Current Version:** v0.9.5.53

This file consolidates Sentinel release notes. Individual historical release-note files may remain in the repository for traceability, but this is the primary release history.

---

## v0.9.5.52 – Segment Order Recovery Guardrails

### Focus

Moves the recovery sprint from pure power scoring into segment integrity. v0.9.5.52 keeps the v0.9.5.51 digit-preserving model, but adds a conservative segment-order tie-breaker for close high-explosion candidates and tightens low-truncation acceptance so row-gap ambiguity does not become false Operational Truth.

### Added

- Segment-order tie-breaker for close 7xxM THP candidate margins.
- Conservative low-truncation acceptance gate: multi-candidate low recovery now needs stronger digit preservation and margin evidence.
- Candidate decision metadata updated to `v0.9.5.52`.
- Regression coverage for Server 553-style close high-explosion candidates and low-truncation ambiguity.

### Changed

- High OCR explosions can recover a near-tie candidate when it better preserves visible rank-segment order.
- Low/truncated THP candidates with close `scale_x10` vs `insert_zero` evidence are quarantined unless the segment is clearly consistent.
- Recovery remains source-local and does not use screenshot filename order, upload order, or Ground Truth as runtime truth.

### Validation

```text
pytest tests/smoke/test_ranking_power_sanity_guard.py tests/smoke/test_operational_import_repository.py tests/smoke/test_ground_truth_validator.py tests/smoke/test_inference_context_engine.py tests/smoke/test_sentinel_data_guard.py -q
31 passed
```

### Commit

```bash
git add .
git commit -m "fix(recovery): add segment-order guardrails for power candidates"
git tag -a v0.9.5.52 -m "v0.9.5.52 Segment Order Recovery Guardrails"
```

---

## v0.9.5.51 – Digit-Preserving Power Recovery

### Focus

Hardens the v0.9.5.50 bidirectional OCR power error model by adding explicit digit-preservation scoring to low/truncated THP candidate recovery. The sprint targets the Server 551/553-style failure mode where a numerically plausible inserted-zero candidate can beat the candidate that better preserves the visible OCR digit evidence.

### Added

- `digit_preservation_score` for power recovery candidates.
- Candidate reasons such as `digit_preservation:0.xxx` in recovery metadata.
- Digit-preserving low-truncation cutover for clear but narrow candidate margins.
- Regression coverage for low-truncation candidate selection.

### Changed

- Low/truncated THP recovery now scores visible digit preservation in addition to local median distance, neighbour order, source-local buckets, rank context, and OCR error model reason.
- Recovery decision metadata now reports `v0.9.5.51`.
- Ambiguous high-explosion and Alliance Power candidates remain margin-gated and quarantined when unclear.

### Guardrail

Digit preservation is not allowed to bypass Data Guard doctrine. It only strengthens candidate scoring for source-local low THP truncation. Runtime still does not use Ground Truth, screenshot filename order, or upload order as truth.

### Validation

```text
python -m compileall -q parser services main.py ground_truth_validator.py sentinel.py version.py
pytest tests/smoke/test_ranking_power_sanity_guard.py tests/smoke/test_thp_power_sanity_guard.py tests/smoke/test_sentinel_ranking_guard.py tests/smoke/test_ranking_recovery.py tests/smoke/test_operational_import_repository.py -q
30 passed
```

Note: full `pytest tests/smoke -q` still collects pre-existing invalid/hotfix smoke files unrelated to this sprint. Targeted Data Guard / Ranking Guard / Recovery tests pass.

### Commit

```bash
git add .
git commit -m "feat(recovery): add digit-preserving power candidate scoring"
git tag -a v0.9.5.51 -m "v0.9.5.51 Digit-Preserving Power Recovery"
```

---

## v0.9.5.50 – Bidirectional Power Error Model

### Focus

Adds an OCR power error model to the existing candidate decision engine. v0.9.5.49 safely quarantined ambiguous high explosions; v0.9.5.50 also detects low/truncated THP values that lost a magnitude digit.

### Added

- Low THP candidate generation for values such as `32,030,601 -> 320,306,010`, `25,009,089 -> 250,009,089/250,090,890`, and `13,861,884 -> 138,618,840`.
- Candidate reasons for:
  - `ocr_error_model:scale_x10_truncated_digit`,
  - `ocr_error_model:scale_x100_truncated_digit`,
  - `ocr_error_model:insert_zero`,
  - `ocr_error_model:leading_digit_to_1/2/3`.
- Regression tests using the Server 549–553 findings.

### Changed

- Candidate scoring now combines source-local context with OCR error probability.
- Clear high-explosion THP candidates can recover when the OCR model creates a decisive margin.
- Low/truncated THP rows recover only when the same source contains a normal THP envelope.

### Guardrail

Recovery remains source-local, auditable, and margin-gated. Runtime does not read Ground Truth; Ground Truth only informed the error classes and tests. Alliance Power low tails remain protected from THP truncation recovery.

### Validation

```text
python -m compileall -q parser main.py ground_truth_validator.py sentinel.py version.py
pytest tests/smoke/test_ranking_power_sanity_guard.py tests/smoke/test_thp_power_sanity_guard.py tests/smoke/test_sentinel_ranking_guard.py tests/smoke/test_ranking_recovery.py tests/smoke/test_operational_import_repository.py -q
30 passed
```

### Commit

```bash
git add .
git commit -m "feat(recovery): add bidirectional OCR power error model"
git tag -a v0.9.5.50 -m "v0.9.5.50 Bidirectional Power Error Model"
```

---

## v0.9.5.49 – Candidate Decision Engine Cutover

### Focus

Replaces the remaining legacy leading-digit recovery decision fallback with a strict candidate decision engine. Candidate generation still considers leading-digit alternatives, but recovery is allowed only when context scoring produces a clear winner.

### Changed

- Removed `legacy_leading_digit_recovery` as a decision path.
- Recovery now requires `best_score >= 0.58` and `margin >= 0.10`.
- Ambiguous candidate sets are moved to `REVIEW - ranking_guard_quarantine`.
- Recovered and ambiguous rows now expose:
  - `power_recovery_decision_strategy`,
  - `power_recovery_decision_version`,
  - `power_recovery_legacy_used`.

### Added

- Regression coverage proving ambiguous Server 553-style candidate ties are quarantined.
- Report trace fields for decision strategy, decision version, and legacy usage.
- Excel export columns for the same decision metadata.

### Guardrail

This sprint intentionally reduces unsafe auto-recovery. If two candidates are nearly tied, Sentinel must quarantine the row rather than promote a guessed value into Operational Truth.

### Validation

```text
python -m compileall -q parser services main.py version.py
pytest tests/smoke/test_ranking_power_sanity_guard.py tests/smoke/test_operational_import_repository.py tests/smoke/test_sentinel_ranking_guard.py tests/smoke/test_ranking_recovery.py -q
23 passed
```

### Commit

```bash
git add .
git commit -m "fix(recovery): remove legacy power recovery fallback"
git tag -a v0.9.5.49 -m "v0.9.5.49 Candidate Decision Engine Cutover"
```

---
## v0.9.5.48 – Source Context Recovery Reportability

### Focus

Makes context-aware power recovery auditable in operational outputs. The sprint does not expand strategic intelligence; it improves explainability of recovered and ambiguous power values.

### Added

- Power candidate metadata columns in Excel exports for THP, Alliance Power, and quarantine sheets.
- `power_recovery` section in `data/latest_import_report.json` with candidate traces, selected value, best/second score, margin, confidence, and decision reason.
- Per-import power recovery counters: recovered rows, candidate traces, and ambiguous candidate counts.
- Regression coverage for Server 553-style candidate trace reporting.

### Fixed

- Global `review_count` now reflects import-level review warnings instead of reporting `0` while import blocks still contain review counts.
- Candidate recovery rows now expose `power_candidate_best`, `power_candidate_second`, `power_candidate_margin`, and `power_recovery_status` directly on the row.

### Guardrail

Recovery remains auditable. If candidate evidence is ambiguous, Sentinel preserves uncertainty through quarantine instead of silently exporting a guessed value.

### Validation

```text
python -m compileall -q parser services main.py version.py
pytest tests/smoke/test_ranking_power_sanity_guard.py tests/smoke/test_operational_import_repository.py tests/smoke/test_sentinel_ranking_guard.py tests/smoke/test_ranking_recovery.py -q
23 passed
```

### Commit

```bash
git add .
git commit -m "feat(reporting): expose power candidate recovery traces"
git tag -a v0.9.5.48 -m "v0.9.5.48 Source Context Recovery Reportability"
```

---

## v0.9.5.47 – Context-aware Power Candidate Recovery

### Focus

Replaces single-candidate leading-digit recovery with a context-aware candidate recovery engine for suspicious THP and Alliance Power values.

### Added

- Multiple power candidate generation for suspicious `7xxM` THP and `77B` Alliance Power rows.
- Source-local candidate scoring using local envelope, neighbour powers, OCR rank context, row position, monotonic ordering, and ranking type.
- Recovery metadata:
  - `power_recovery_candidates`
  - `power_recovery_selected_score`
  - `power_recovery_selected_reason`
  - `power_recovery_method=<ranking_type>_context_candidate_recovery`
- Ambiguous candidate metadata for quarantine/review paths.
- Regression coverage for Server 553 candidate recovery, including a `764M -> 224M` case when local context clearly supports the 224M candidate.

### Changed

- Power recovery now scores multiple candidates before accepting a correction.
- Legacy deterministic leading-digit recovery remains as a guarded fallback for previously covered safe cases.
- Version updated to `0.9.5.47`.

### Guardrail

Candidate recovery remains source-local. It does not use screenshot filename order, upload order, or cross-user batch order as truth.

### Validation

```text
python -m compileall -q parser main.py version.py
pytest tests/smoke/test_ranking_power_sanity_guard.py tests/smoke/test_thp_power_sanity_guard.py tests/smoke/test_sentinel_ranking_guard.py tests/smoke/test_ranking_recovery.py -q
24 passed
```

### Commit

```bash
git add .
git commit -m "feat(recovery): add context-aware power candidate recovery"
git tag -a v0.9.5.47 -m "v0.9.5.47 Context-aware Power Candidate Recovery"
```

---

## v0.9.5.46 – Documentation Consolidation

### Focus

Consolidates Sentinel documentation after the Data Guard, Ranking Guard, Power Sanity Guard, and Source-local Power Digit Recovery sprints. No runtime parser behavior is changed.

### Added

- `docs/START_NEXT_CHAT.md` for clean handoff into a new chat.
- `docs/LESSONS_LEARNED.md` to preserve project knowledge and failed/successful hypotheses.
- `docs/ARCHITECTURAL_DECISIONS.md` for ADR-style decision memory.

### Changed

- Updated `docs/PROJECT_STATUS.md` to the actual v0.9.5.45 baseline.
- Updated `docs/ROAD_TO_V1.md` with milestones from Data Integrity Fortress to v1.0.0.
- Updated `docs/ARCHITECTURE.md`, `docs/README.md`, `docs/SENTINEL.md`, `docs/VISION.md`, `docs/ROADMAP.md`, `docs/INTELLIGENCE.md`, `docs/MODUS_OPERANDI.md`, and `docs/SENTINEL_DATA_GUARD.md`.
- Updated `version.py` to `0.9.5.46`.

### Key documented finding

The next development sprint should implement context-aware power candidate recovery. v0.9.5.45 can reduce false `7xxM`/`77B` power explosions, but single leading-digit substitution is not enough to choose the correct candidate in all cases.

### Validation

Documentation-only sprint. Expected validation:

```bash
python -m compileall -q .
```

### Commit

```bash
git add .
git commit -m "docs(project): consolidate Sentinel handoff documentation for v0.9.5.46"
git tag -a v0.9.5.46 -m "v0.9.5.46 Documentation Consolidation"
```

---

## Source: `RELEASE_NOTES_PATCH10A.md`

# Sentinel v0.9.5.30 – Universal Server Detection

## Focus

Generalize server detection for mobile and localized screenshots without changing OCR, parser, Data Guard, Ranking Guard, Recovery, or Inference behavior.

The blind Server 552 mobile test showed that German mobile screenshots expose server evidence as repeated row-level values such as `Kriegszone #552`, while the existing detector was still Warzone/header-oriented. Sentinel correctly moved all screenshots to review instead of guessing, but the candidate extractor failed to surface the already-visible `#552` evidence.

## Added

- Pattern-first server candidate extraction for language-neutral `#123` / `#1234` OCR tokens.
- Support for full-width `＃` hash tokens.
- Localized fallback patterns for common labels such as `Kriegszone`, `Zona`, and `Zone de guerre`.
- Smoke tests for:
  - repeated mobile `#552` candidates,
  - localized `Kriegszone #552` candidates,
  - ambiguous hash candidates that must remain review.

## Changed

- Server candidate extraction now collects hash-number candidates before language-specific label patterns.
- Existing consensus and Data Guard logic remain authoritative.
- Version updated to `0.9.5.30`.

## Guardrail

This release does not guess a server from filenames, timestamps, upload source, or session context.

A server is accepted only when repeated intrinsic OCR evidence reaches the existing consensus threshold. Ambiguous or insufficient candidates still go to review.

## Validation

```text
python -m pytest tests/smoke/test_warzone_consensus.py tests/smoke/test_sentinel_data_guard.py tests/smoke/test_operational_import_repository.py -q
11 passed
```

## Commit

```bash
git add .
git commit -m "feat(server): add pattern-based universal server detection"
git tag -a v0.9.5.30 -m "v0.9.5.30 Universal Server Detection"
```

---

# Sentinel v0.9.5.29 – Ranking Guard Recovery

## Focus

Introduces a conservative Ranking Guard Recovery layer after the Ranking Guard and before quarantine.

The goal is not to guess corrected rankings. The goal is to recover only rows whose ranking-type assignment is provably safe, and to calibrate false-positive alliance-name shapes that previously filled quarantine.

## Added

- `parser/ranking_recovery.py`
  - Evidence-based recovery decisions for Ranking Guard quarantines.
  - Explicit distinction between `recovered`, `calibrated_pass`, and `quarantine`.
  - Safe THP recovery only when explicit player fields and player-scale power are present.
  - Alliance Power calibration for rows where bracketed alliance names mimic player tags but no explicit player fields exist.
- Ranking recovery metrics in `data/latest_import_report.json`:
  - attempts,
  - success,
  - calibrated_pass,
  - rejected,
  - confidence_avg.
- Smoke tests for Ranking Guard Recovery.

## Changed

- `parser/ranking_guard.py` now gives the recovery layer one conservative chance before quarantine.
- Ranking Guard remains the integrity gate; Recovery cannot bypass it.
- Rows recovered or calibrated by the recovery layer are annotated with explainable evidence fields.
- Version updated to `0.9.5.29`.

## Guardrail

Recovery is evidence-based only.

A row is not moved because it is convenient. It is moved only if row-level evidence proves a safer destination. If evidence is insufficient, quarantine remains the correct outcome.

## Validation

```text
python -m pytest tests/smoke/test_ranking_recovery.py tests/smoke/test_sentinel_ranking_guard.py tests/smoke/test_operational_import_repository.py -q
```

## Commit

```bash
git add .
git commit -m "feat(ranking): add evidence-based ranking guard recovery"
git tag -a v0.9.5.29 -m "v0.9.5.29 Ranking Guard Recovery"
```


# v0.9.5.35 – THP Power Sanity Guard

Adds a conservative THP-only sanity guard that quarantines late-scroll power outliers before final rank merge. This protects Operational Truth from OCR digit spikes while keeping OCR and parser behavior unchanged.


---

## Source: `RELEASE_NOTES_v0.9.5.30.md`

# Sentinel v0.9.5.30 – Universal Server Detection

## Focus

Generalize server detection for mobile and localized screenshots without changing OCR, parser, Data Guard, Ranking Guard, Recovery, or Inference behavior.

The blind Server 552 mobile test showed that German mobile screenshots expose server evidence as repeated row-level values such as `Kriegszone #552`, while the existing detector was still Warzone/header-oriented. Sentinel correctly moved all screenshots to review instead of guessing, but the candidate extractor failed to surface the already-visible `#552` evidence.

## Added

- Pattern-first server candidate extraction for language-neutral `#123` / `#1234` OCR tokens.
- Support for full-width `＃` hash tokens.
- Localized fallback patterns for common labels such as `Kriegszone`, `Zona`, and `Zone de guerre`.
- Smoke tests for:
  - repeated mobile `#552` candidates,
  - localized `Kriegszone #552` candidates,
  - ambiguous hash candidates that must remain review.

## Changed

- Server candidate extraction now collects hash-number candidates before language-specific label patterns.
- Existing consensus and Data Guard logic remain authoritative.
- Version updated to `0.9.5.30`.

## Guardrail

This release does not guess a server from filenames, timestamps, upload source, or session context.

A server is accepted only when repeated intrinsic OCR evidence reaches the existing consensus threshold. Ambiguous or insufficient candidates still go to review.

## Validation

```text
python -m pytest tests/smoke/test_warzone_consensus.py tests/smoke/test_sentinel_data_guard.py tests/smoke/test_operational_import_repository.py -q
11 passed
```

## Commit

```bash
git add .
git commit -m "feat(server): add pattern-based universal server detection"
git tag -a v0.9.5.30 -m "v0.9.5.30 Universal Server Detection"
```


---

## Source: `RELEASE_NOTES_v0.9.5.31.md`

# Sentinel v0.9.5.31 – Mobile Ranking Type Integrity Hotfix

## Focus

Fixes a blind-test issue found on Server 552 mobile German screenshots where lower Alliance Power pages were inferred as Total Hero Power after their values dropped below 1B.

## Fixed

- Detects German mobile ranking headers:
  - `Allianz-Kampfkraft` → `alliance_power`
  - `Gesamtkampfkraft der Helden` → `total_hero_power`
- Prevents low-rank Alliance Power rows from leaking into THP merely because their values are player-scale.
- Keeps genuine low-rank Alliance Power rows in Alliance Power when the source screen is classified as Alliance Power and the row has alliance-name-only shape.
- Keeps top-rank THP-shaped rows in Alliance Power quarantined instead of blindly accepting them.

## Guardrail

This patch does **not** weaken the Data Guard doctrine. It does not guess a ranking type from filenames or timestamps. It uses intrinsic screen/header evidence and conservative row-shape calibration.

## Validation

```text
10 passed
```

Targeted tests:

```bash
pytest tests/smoke/test_mobile_german_ranking_type_detection.py \
       tests/smoke/test_ranking_recovery.py \
       tests/smoke/test_sentinel_ranking_guard.py \
       tests/smoke/test_ranking_type_fallback.py -q
```

## Commit

```bash
git add .
git commit -m "fix(import): preserve mobile alliance ranking type integrity"
git tag -a v0.9.5.31 -m "v0.9.5.31 Mobile Ranking Type Integrity Hotfix"
```


---

## Source: `RELEASE_NOTES_v0.9.5.32.md`

# Sentinel v0.9.5.32 – Semantic Ranking Guard

## Focus

Fixes the remaining mobile Server 552 ranking-type integrity issue by making the Ranking Guard semantic instead of power-threshold driven.

## Fixed

- Bracketed alliance names such as `[drr] Young Tokai Teio` are no longer treated as player evidence by themselves.
- Low-power Alliance Power rows below 1B are allowed when they come from an Alliance Power screen and only contain generic alliance-name fields.
- THP rows still require explicit player-ranking fields (`alliance_tag`, `player_name`, or `hero_power`) before they can be recovered into `total_hero_power`.
- German column headers are now accepted as ranking-type evidence:
  - `Allianzname` → `alliance_power`
  - `Kommandant` → `total_hero_power`

## Changed

- Ranking Guard scoring now separates explicit player fields from bracketed tags inside generic alliance names.
- Power remains supporting evidence only; it is no longer sufficient to classify low-power alliance rows as THP.
- Existing Ranking Recovery remains conservative and only reclassifies rows when explicit player fields are present.

## Validation

```text
pytest tests/smoke/test_semantic_ranking_guard.py \
       tests/smoke/test_mobile_german_ranking_type_detection.py \
       tests/smoke/test_sentinel_ranking_guard.py \
       tests/smoke/test_ranking_recovery.py -q

14 passed
```

Full smoke collection still contains pre-existing invalid legacy smoke files unrelated to this patch.

## Commit

```bash
git add .
git commit -m "fix(ranking): add semantic Ranking Guard field evidence"
git tag -a v0.9.5.32 -m "v0.9.5.32 Semantic Ranking Guard"
```


---

## Source: `RELEASE_NOTES_v0.9.5.34.md`

# Sentinel v0.9.5.34 – Mobile Ranking Boundary Hotfix

## Focus

Fixes a mobile German Total Hero Power detection issue where generic `Allianzname` column evidence could outweigh `Kommandant` player-ranking evidence.

## Fixed

- Ranking type detection is now evidence-scored instead of first-match based.
- `Kommandant` / `Commander` evidence wins over generic alliance-name column labels on THP screens.
- `Allianz-Kampfkraft` remains strong Alliance Power title evidence.
- Prevents the first mobile THP screenshot from being appended to the Alliance Power sheet.

## Validation

```text
pytest tests/smoke/test_mobile_german_ranking_type_detection.py tests/smoke/test_semantic_ranking_guard.py -q
```

## Commit

```bash
git add .
git commit -m "fix(ranking): prioritize commander evidence for mobile THP screens"
git tag -a v0.9.5.34 -m "v0.9.5.34 Mobile Ranking Boundary Hotfix"
git push origin main
git push origin v0.9.5.34
```


---

## Source: `RELEASE_NOTES_v0.9.5.35.md`

# Sentinel v0.9.5.35 – THP Power Sanity Guard

## Focus

Protect Total Hero Power exports from OCR digit outliers that are locally inconsistent with their screenshot context.

## Fixed

- Prevents late-scroll THP OCR spikes such as `198M -> 798M` from being promoted to top ranks by the final power-order merge.
- Suspicious THP values are quarantined with explainable `thp_power_sanity` evidence instead of being silently imported.
- Keeps valid first-screen THP whales untouched; the guard only applies to later THP screenshots with local outlier evidence.

## Added

- `parser/thp_sanity_guard.py`
- THP local median outlier detection.
- Quarantine metadata:
  - `quarantine_reason = thp_power_sanity_outlier`
  - `ranking_guard_warning = thp_power_sanity:...`
  - `thp_sanity_local_median`
- Smoke tests for:
  - late-scroll THP outlier quarantine,
  - real first-screen whales allowed,
  - normal scroll overlap allowed.

## Validation

```text
python -m compileall -q parser main.py
pytest tests/smoke/test_thp_power_sanity_guard.py tests/smoke/test_semantic_ranking_guard.py tests/smoke/test_sentinel_ranking_guard.py tests/smoke/test_mobile_german_ranking_type_detection.py tests/smoke/test_power_first_reconstruction.py -q
16 passed
```

## Commit

```bash
git add .
git commit -m "fix(data-guard): quarantine THP power outliers before rank merge"
git tag -a v0.9.5.35 -m "v0.9.5.35 THP Power Sanity Guard"
git push origin main
git push origin v0.9.5.35
```


---

## Source: `RELEASE_NOTES_v0.9.5.36.md`

# Sentinel v0.9.5.36 – Ranking Power Monotonicity Guard

## Focus

Generalize the THP Power Sanity Guard into a ranking-wide power envelope guard.

This release protects both `total_hero_power` and `alliance_power` exports from OCR digit outliers before the final power-order merge can promote impossible values to the top of a ranking.

## Fixed

- Prevents Alliance Power OCR spikes such as `23B -> 79B` from being promoted to top ranks.
- Keeps legitimate low-power alliance tail ranks below 1B intact.
- Preserves v0.9.5.35 THP behavior for late-scroll `198M -> 798M`-style outliers.
- Adds rank-aware grace for genuine top Alliance Power leaders.

## Added

- `parser/ranking_power_sanity_guard.py`
- Generic local power-envelope validation for guarded ranking types.
- Alliance Power outlier quarantine metadata:
  - `quarantine_reason = alliance_power_sanity_outlier`
  - `ranking_guard_warning = power_sanity:alliance_power_outlier;...`
  - `power_sanity_local_median`
  - `power_sanity_local_ratio`
- Backward-compatible `parser/thp_sanity_guard.py` wrapper.
- Smoke tests for:
  - Alliance Power local outlier quarantine,
  - legitimate low-power Alliance Power tails,
  - real rank-1 Alliance Power leaders,
  - existing THP sanity guard behavior.

## Validation

```text
python -m compileall -q parser main.py
pytest tests/smoke/test_ranking_power_sanity_guard.py tests/smoke/test_thp_power_sanity_guard.py tests/smoke/test_semantic_ranking_guard.py tests/smoke/test_sentinel_ranking_guard.py tests/smoke/test_mobile_german_ranking_type_detection.py tests/smoke/test_power_first_reconstruction.py -q
19 passed
```

## Commit

```bash
git add .
git commit -m "fix(data-guard): quarantine ranking power outliers before merge"
git tag -a v0.9.5.36 -m "v0.9.5.36 Ranking Power Monotonicity Guard"
git push origin main
git push origin v0.9.5.36
```


---

## Source: `RELEASE_NOTES_v0.9.5.37.md`

# Sentinel v0.9.5.37 – Screenshot-Aware Ranking Power Guard

## Focus

Turns the Ranking Power Guard from a strict local median filter into a screenshot/rank-aware context validator.

## Fixed

- Legitimate top-3 Alliance Power rows are no longer quarantined when mobile screenshots split the top ranks across adjacent captures.
- Server 552 Alliance Power top rows such as 79B / 77B / 70B are allowed when rank context marks them as true top ranks.
- Lower-rank Alliance Power OCR explosions remain quarantined before power sorting.
- THP Power Sanity behavior from v0.9.5.35 remains unchanged.

## Guardrails

- Added an absolute Alliance Power ceiling so catastrophic top-rank digit explosions are still quarantined.
- Quarantine remains preferred over silent correction.

## Validation

```text
pytest tests/smoke/test_ranking_power_sanity_guard.py tests/smoke/test_thp_power_sanity_guard.py tests/smoke/test_semantic_ranking_guard.py tests/smoke/test_sentinel_ranking_guard.py tests/smoke/test_mobile_german_ranking_type_detection.py tests/smoke/test_power_first_reconstruction.py -q
```


---

## Source: `RELEASE_NOTES_v0.9.5.38.md`

# Sentinel v0.9.5.38 – Top Rank Alliance Power Allowance

## Focus

Fixes an over-conservative Ranking Power Sanity Guard decision where real top Alliance Power rows from early mobile screenshots were quarantined because OCR rank anchors were missing before final reconstruction.

## Fixed

- Allows very high Alliance Power values in the first two Alliance Power source screenshots even when `ocr_rank` is missing.
- Keeps the absolute Alliance Power safety ceiling in place.
- Keeps late-source Alliance Power outlier quarantine active.
- Keeps THP Power Sanity behavior unchanged.

## Why

Mobile screenshots may split the real Top 3 Alliance Power rows across the first two source images. Before final export, those rows can lack rank anchors, so a rank-only Top 3 exception is not enough. Sentinel now treats early screenshot source position as supporting context while still quarantining late-scroll explosions.

## Validation

```text
pytest tests/smoke/test_ranking_power_sanity_guard.py tests/smoke/test_thp_power_sanity_guard.py tests/smoke/test_semantic_ranking_guard.py tests/smoke/test_sentinel_ranking_guard.py tests/smoke/test_mobile_german_ranking_type_detection.py tests/smoke/test_power_first_reconstruction.py -q
```

## Commit

```bash
git add .
git commit -m "fix(ranking-guard): allow early top alliance power rows without rank anchors"
git tag -a v0.9.5.38 -m "v0.9.5.38 Top Rank Alliance Power Allowance"
```


---

## Source: `RELEASE_NOTES_v0.9.5.39.md`

# Sentinel v0.9.5.39 – General Top Alliance Power Allowance

## Focus

Finalizes the Ranking Power Sanity Guard behavior for multi-server regression runs.

## Fixed

- Generalizes the top Alliance Power allowance introduced for Server 552 so it also protects legitimate top-of-source rows from desktop captures.
- Prevents real leading alliances such as strong Server 550/551 Alliance Power rows from being quarantined only because their screenshot-local median is much lower.
- Preserves quarantine behavior for late-row Alliance Power spikes and late-scroll THP OCR outliers.

## Validation

```text
pytest tests/smoke/test_ranking_power_sanity_guard.py -q
pytest tests/smoke -q
```

Expected operational validation:

```text
python main.py
python ground_truth_validator.py
```

## Commit

```bash
git add .
git commit -m "fix(ranking): generalize top alliance power allowance"
git tag -a v0.9.5.39 -m "v0.9.5.39 General Top Alliance Power Allowance"
```


---

## Source: `RELEASE_NOTES_v0.9.5.40.md`

# Sentinel v0.9.5.40 – Alliance Power Shape Guard

## Focus

Finalizes the Alliance Power power-sanity path after the 68-screenshot regression run showed that simple top-of-source allowances were too broad.

## Fixed

- Blocks source-local 50B+ Alliance Power high clusters such as the false Server 552 `79B / 77B / 70B` OCR spikes.
- Keeps legitimate lower Alliance Power leaders such as Server 550 `WARF / LsC` and Server 551 `Hsg` out of quarantine.
- Avoids using global screenshot order, filenames, timestamps, or cross-user batch order as truth.
- Preserves the existing THP late-scroll outlier guard.
- Keeps absolute Alliance Power ceiling protection.

## Added

- Source-local Alliance Power shape detector in `parser/ranking_power_sanity_guard.py`.
- Regression coverage for false 552 high clusters and legitimate 550/551 top-of-source rows.
- More explicit `source_shape_high_cluster` quarantine evidence.

## Validation

```text
pytest tests/smoke/test_ranking_power_sanity_guard.py tests/smoke/test_thp_power_sanity_guard.py tests/smoke/test_semantic_ranking_guard.py tests/smoke/test_sentinel_ranking_guard.py tests/smoke/test_mobile_german_ranking_type_detection.py tests/smoke/test_power_first_reconstruction.py -q
25 passed
```

## Commit

```bash
git add .
git commit -m "fix(ranking-guard): add alliance power source-shape sanity guard"
git tag -a v0.9.5.40 -m "v0.9.5.40 Alliance Power Shape Guard"
```


---

## Source: `RELEASE_NOTES_v0.9.5.41.md`

# Sentinel v0.9.5.41 – High-Cluster Alliance Power Guard

## Focus

Finalizes the Alliance Power source-shape guard for paired high OCR spikes.

## Fixed

- Blocks paired 50B+ Alliance Power OCR spikes at the top of a single source when the remaining visible source envelope is far lower.
- Extends the v0.9.5.40 source-shape guard so 552-style `79B / 77B / 70B` false high cluster is fully quarantined.
- Keeps legitimate 550/551 Alliance Power leaders such as `WARF`, `LsC`, and `Hsg` allowed.
- Keeps THP outlier behavior unchanged.

## Guardrail

The guard remains source-local. It does not rely on screenshot filename order, upload order, or multi-user batch order.

## Validation

```text
python -m compileall -q parser main.py ground_truth_validator.py sentinel.py
pytest tests/smoke/test_ranking_power_sanity_guard.py -q
9 passed
```

Full test collection still contains pre-existing legacy smoke-test issues unrelated to this patch.


---

## Source: `RELEASE_NOTES_v0.9.5.42.md`

# Sentinel v0.9.5.42 – Ranking Segment Integrity Guard

## Focus

Protect ranking reconstruction from scroll-segment contamination without relying on screenshot filename order.

## Added

- Intrinsic THP rank/power envelope guard.
- Late-scroll THP rows with high OCR ranks and impossible top-whale powers are quarantined before final power sorting.
- Alliance Power rank/power envelope guard for non-top rows with impossible 50B+ values.
- Explainable quarantine reasons:
  - `thp_rank_power_envelope_violation`
  - `alliance_rank_power_envelope_violation`

## Why

Server 553 showed a new failure mode: late-scroll THP screenshots containing ranks around 100 were parsed with OCR digit explosions around 764M and then sorted above the real Rank 1 player. Earlier guards relied too much on source order, which is unsafe when future Discord or multi-user uploads can mix screenshots from different rankings.

This patch uses row-intrinsic evidence instead: OCR rank plus parsed power. A row that claims to be Rank 100 but carries a top-whale power value is not trusted. It is quarantined, not repaired.

## Expected impact

- Server 553 false THP leaders such as late-rank 764M rows should move to `REVIEW - ranking_guard_quarantine`.
- Server 553 Alliance Power false 77B non-top row should be quarantined.
- Existing 549–552 protections remain intact because the guard is intrinsic and conservative.

## Validation

```text
python -m compileall -q parser main.py ground_truth_validator.py
python main.py
python ground_truth_validator.py
```

## Commit

```bash
git add .
git commit -m "fix(ranking-guard): add intrinsic segment integrity guard"
git tag -a v0.9.5.42 -m "v0.9.5.42 Ranking Segment Integrity Guard"
git push origin main
git push origin v0.9.5.42
```


---

## Source: `RELEASE_NOTES_v0.9.5.43.md`

# Sentinel v0.9.5.43

## Fix

Adds a THP source-shape digit explosion guard.

The guard detects a mixed screenshot source where late-scroll rows around ~160M THP are present, but neighbouring rows from the same source are misread as ~760M/~790M and incorrectly jump to the top after power sorting.

## Principles

- Source-local only.
- No reliance on screenshot order, upload order, or filename order as truth.
- OCR rank remains weak evidence.
- Rank-conflict evidence is required before the high cluster is blocked.
- Quarantine remains preferred over false operational truth.

## Validation

```text
26 passed
```


---

## Source: `RELEASE_NOTES_v0.9.5.44.md`

# Sentinel v0.9.5.44

## Focus

Targeted Ranking Power Sanity Guard hardening for Server 553 imports.

## Fixed

- Quarantines complete THP digit-explosion clusters when one row in the same impossible high cluster lacks a rank-conflict warning.
- Prevents a false 7xx-M THP row from surviving as rank 1 after adjacent 7xx-M rows are already quarantined.
- Quarantines source-local Alliance Power middle spikes such as a 77B value appearing after lower visible rank-1..4 rows in the same screenshot.
- Keeps the rule source-local: no reliance on screenshot filename order, upload order, or cross-user screenshot sequence.

## Why

Server 553 showed two remaining failure classes:

1. THP rows from late-scroll screenshots could be OCR-read as 7xx-M values and jump to the top after sorting.
2. Alliance Power values could gain an extra leading digit inside the same visible screenshot block, e.g. an 11.7B row becoming 77.7B.

Both are intrinsic source-shape problems, not server-order problems.

## Validation

```text
pytest tests/smoke/test_ranking_power_sanity_guard.py -q
11 passed
```

## Commit

```bash
git add .
git commit -m "fix(ranking-guard): harden source-local power sanity for v0.9.5.44"
git tag -a v0.9.5.44 -m "v0.9.5.44 Source-local Power Sanity Guard"
```


---

## Source: `RELEASE_NOTES_v0.9.5.45.md`

# Sentinel v0.9.5.45

## Focus

Field-level power recovery for mobile OCR leading-digit explosions.

## Added

- Source-local leading-digit recovery for THP values such as `764,292,586 -> 164,292,586` when rank/source context supports the correction.
- Source-local leading-digit recovery for Alliance Power values such as `77,739,565,950 -> 17,739,565,950` when the row is not a valid top-3 leader and the recovered value fits the local ranking envelope.
- Recovery metadata on corrected rows:
  - `power_original`
  - `power_recovered_from`
  - `power_recovery_method`
  - `power_sanity_status=recovered`

## Changed

- Ranking Power Sanity Guard no longer only quarantines this specific recoverable OCR class.
- Values are recovered only when intrinsic rank/source evidence is strong enough.
- The guard still quarantines suspicious values when no safe recovery candidate exists.

## Why

Server 553 proved that the v0.9.5.44 guard correctly identified false 7xx-M THP and 77B Alliance Power values, but it preserved them only in quarantine. The screenshots show that many of these values are recoverable leading-digit OCR errors rather than unusable rows.

Sentinel should not invent truth. But when the source-local evidence supports a deterministic field-level recovery, preserving the row with explicit recovery metadata is better than dropping useful data into review.

## Validation

```text
python -m compileall -q parser main.py version.py
pytest tests/smoke/test_ranking_power_sanity_guard.py tests/smoke/test_thp_power_sanity_guard.py tests/smoke/test_sentinel_ranking_guard.py tests/smoke/test_ranking_recovery.py -q
23 passed
```

## Commit

```bash
git add .
git commit -m "fix(ranking-guard): recover source-local leading digit power errors"
git tag -a v0.9.5.45 -m "v0.9.5.45 Source-local Power Digit Recovery"
```

## v0.9.5.60 - Command Center Consolidation

This release consolidates Sentinel's operator-facing review workflow. Review history now uses a stable business identity based on server, ranking type, rank, screenshot, problem type, and reason. Re-running the same screenshots updates `last_seen_at` and `seen_count` instead of creating duplicate open reviews.

The web navigation now exposes a dedicated Review Center at `/reviews`. Existing static output files remain available as run-detail/evidence views during the transition, but the intended operator path is now Command Center -> Reviews -> Evidence.

No OCR, recovery, Ranking Guard, or Data Guard decision logic was changed.

---

## v0.9.5.62 - Visible Navigation Consolidation

### Focus

Make the Command Center information architecture visible and navigable for operators.

### Added

- A persistent top workflow bar across web pages: Command -> Imports -> Quality -> Reviews -> Exports.
- Wider sidebar navigation with readable labels, descriptions, and grouped sections.
- Cross-links from Command Center to Imports, Quality, and Reviews.
- Cross-links from Imports to Quality, Reviews, and the latest static run report.
- Cross-links from Quality back to Imports, into Reviews, and onward to Exports.
- Review detail route at `/reviews/{history_key}` with choices, why-bullets, resolution form, and explainability trace.
- CSS for consistent workflow cards, review detail cards, forms, and responsive navigation.

### Changed

- Review Evidence is no longer only a static-output concept; the web app now has a first-class detail route for persistent review-history entries.
- The visible operator flow now matches the intended architecture: ingestion evidence, trust assessment, human decision, then export/reporting.
- Version updated to `0.9.5.62`.

### Guardrail

This sprint changes presentation and navigation only. It does not alter OCR, Data Guard, Ranking Guard, recovery, quarantine, Operational Truth, or Excel export logic.

### Validation

```text
pytest tests/smoke/test_web_navigation_consolidation.py tests/smoke/test_command_center.py -q
9 passed
python -m compileall -q web/app.py web/navigation.py web/routes web/templates version.py
```

## v0.9.5.63 - Human Review Screenshot Evidence

Focus: make visual evidence directly reachable from the Review Center and Review Detail pages.

### Added
- Review Detail now shows a dedicated Screenshot Evidence panel with a clickable preview.
- Screenshot filenames in Review Detail open the source screenshot in a new browser tab.
- Review Queue screenshot references are clickable links.
- Web app now mounts `/screenshots` as a read-only static evidence route.

### Guardrails
- Screenshot links are generated from safe basenames only. Persisted review JSON cannot inject path traversal into screenshot URLs.
- The change improves human review UX only. It does not alter OCR, Data Guard, Ranking Guard, review decisions, or Operational Truth.

### Validation
- Added smoke coverage for screenshot links, preview markup, and the `/screenshots` static mount.
- Version updated to `0.9.5.63`.

## v0.9.5.64 - Review Evidence Highlight Overlay

Focus: make Review Detail faster for human operators by reducing screenshot dominance and visually highlighting the affected rank.

### Added
- Two-column Review Detail layout: decision workflow on the left, screenshot evidence on the right.
- Compact screenshot preview that keeps the review problem, candidates, and resolve form visible.
- Target-rank highlight overlay on screenshot previews using the review's rank and ranking type.
- Screenshot evidence metadata panel showing target ranking, filename, and full-resolution action.
- Consolidated `/docs/PATCH_SUMMARY.md` as the canonical patch-summary register for future releases.

### Guardrails
- The overlay is a UI guide only. It does not crop, mutate, reinterpret, or replace the source screenshot.
- The original screenshot remains available through an open-in-new-tab link.
- OCR, Data Guard, Ranking Guard, recovery, quarantine, Operational Truth, and Excel exports remain unchanged.

### Validation
- Extended smoke coverage for Review Detail layout, rank highlight markup, and rank highlight URL enrichment.
- Version updated to `0.9.5.64`.

## v0.9.5.65 - Screenshot Highlight Calibration

### Fixed

- Corrected the screenshot rank-highlight overlay that could land too low in Review Detail.
- Added ranking-type overlay profiles for alliance and hero ranking screenshots.

### Improved

- Review choices now display power values with German-style thousands separators for faster human review.
- Highlight metadata can mark a target as approximate when the computed row would be outside the visible screenshot.

### Version

- Version updated to `0.9.5.65`.

## v0.9.5.66 - Operational Readiness Drilldown

Focus: make the Command Center start page answer whether Sentinel's current server dataset is operational and where the Proud Owner must act next.

### Added
- Operational Readiness section on the Command Center start page.
- Drill-down KPI cards for Servers Discovered, Operational, Pending Review, Missing Data, and Failed Imports.
- Server health strip showing per-server operational state directly on the Command Center.
- Links from each status card to the relevant workflow page: Servers, Reviews, Quality, or Imports.
- Drill-down notices on Imports, Quality, Servers, and Reviews when opened from Operational Readiness filter links.

### Guardrails
- This sprint changes web visibility and navigation only.
- OCR, Data Guard, Ranking Guard, recovery, quarantine, Operational Truth, and Excel exports remain unchanged.
- Pending Review is intentionally counted before Missing Data because open human decisions block Operational Truth even when source coverage exists.

### Validation
- Added smoke coverage for the Operational Readiness cards, drill-down links, server health strip, and filter-aware destination pages.
- Version updated to `0.9.5.66`.

## v0.9.5.67 - Operational Readiness Correctness

Focus: make the Command Center readiness drill-downs technically safe and semantically aligned with current-run Operational Truth.

### Fixed
- Server drill-down cards no longer crash when the historical SQLite database is empty or missing runtime tables.
- `/servers` and `/servers?status=operational` now degrade to a current-run server landscape instead of requiring historical ranking tables.
- `/servers/{server}` now has a safe current-run fallback when historical intelligence is unavailable.
- `Missing Data` drill-down no longer surfaces benchmark/ground-truth Server 551 as if it belonged to the current import.

### Improved
- Command Center readiness now uses operational server coverage, not raw import readiness.
- The old ambiguous 50% Operational Readiness card now reads as Operational Coverage and shows operational servers versus total servers.
- Mission review count now prefers open human-review history / review items instead of raw Data Guard warning counts.
- Review effort label now says `Estimated review effort: 2–5 min` so the time estimate is explicit.
- Data Guard metric labels raw warning counts as raw warnings to avoid confusing row-level warnings with human review items.

### Guardrails
- Benchmark and ground-truth quality reports remain available, but they are no longer used as the visible current-run missing-data drill-down.
- Historical intelligence remains optional; empty ZIP-packed SQLite files no longer break operational navigation.
- OCR, Ranking Guard, Data Guard, recovery, review decisions, Operational Truth, and exports remain unchanged.

### Validation
- Added smoke coverage for Operational Readiness drill-down routes with an empty database.
- Added smoke coverage ensuring current-run Missing Data does not show benchmark Server 551.
- Version updated to `0.9.5.67`.

## v0.9.5.68 - Historical Dataset Import & Coverage Baseline

This release adds a dedicated historical Excel import path so Sentinel can build a broader server coverage baseline from the existing `/input` workbooks.

### Highlights
- Added `importer/historical_excel_import.py`.
- Imports supported historical sheets from:
  - `LastWarS5_post_Transfer.xlsx`
  - `LastWarS6_pre-season.xlsx`
- Writes an audit report to `data/historical_import_report.json`.
- Stores historical rankings in SQLite collections with `historical_*` collection types.
- Command Center Operational Readiness can now include historical server/ranking coverage in addition to latest import and review state.

### Why it matters
The Command Center can now answer a broader question: not only what happened in the latest OCR run, but which servers are known in the historical dataset and which core ranking feeds are still missing.

### Safety
Historical data is reference data. It does not replace current-run OCR evidence and it does not automatically change Operational Truth.

### Validation
```text
5 passed
compileall importer/historical_excel_import.py application/command_center/service.py web/templates/command_center.html version.py passed
```

### Commit
```bash
git add .
git commit -m "feat(import): load historical Excel coverage baseline"
git tag -a v0.9.5.68 -m "v0.9.5.68 Historical Dataset Import and Coverage Baseline"
```

## v0.9.5.69 - Historical Import Performance Fix

Focus: make historical Excel import fast, observable, and safe for the S5/S6 baseline workbooks.

### Fixed
- Replaced per-row SQLite writes with cached bulk writes inside a sheet-level transaction.
- Added `--verbose` progress output for file/sheet-level import visibility.
- Removed the slow computed-rank monkey-patch flow and computes ranks directly in memory.
- Writes a partial import report even when an import is interrupted or fails.

### Improved
- Caches collections, ranking types, snapshots, and entities during import.
- Limits processing to the explicitly supported historical workbook sheets.
- Reports per-collection duration, status, imported rows, skipped rows, and covered servers.
- Keeps historical imports as reference data only; no Operational Truth, latest OCR report, review history, or export behavior is changed.

### Validation
```text
2 passed tests/smoke/test_historical_excel_import.py
Actual workbook import: 3024 rows, 128 servers, importer duration 1.16s
compileall importer/historical_excel_import.py version.py passed
```

### Command
```bash
python importer/historical_excel_import.py --input-dir input --report data/historical_import_report.json --verbose
```

### Commit
```bash
git add .
git commit -m "fix(import): speed up historical excel import"
git tag -a v0.9.5.69 -m "v0.9.5.69 Historical Import Performance Fix"
```

## v0.9.5.70 - Historical Import Integrity & Coverage Drilldown

This release makes the historical Excel baseline visible in the Command Center workflow. The Import Center now distinguishes current OCR imports from historical reference imports, and the Quality missing-data drilldown explains which servers are incomplete without mixing in benchmark/ground-truth validation views.

- Added historical import dashboard service.
- Added historical import report panels to Imports.
- Added SQLite historical snapshot coverage table.
- Added historical baseline metrics to Missing Data drilldown.
- Preserved the rule that historical data is reference coverage, not automatic Operational Truth.

```bash
git add .
git commit -m "feat(import): expose historical coverage drilldown"
git tag -a v0.9.5.70 -m "v0.9.5.70 Historical Import Integrity and Coverage Drilldown"
```

# Sentinel v0.9.5.71 – Snapshot Management Foundation

This release introduces explicit managed snapshots for screenshot upload work. A reviewer can now create an active import context such as `S6 pre Transfer` before uploading or processing screenshots. Sentinel displays that active snapshot in the Command Center and Import Center so data can be tied to a human-readable operational phase.

## Highlights

- Managed snapshot storage in `data/managed_snapshots.json`.
- Import Center `Create Snapshot` workflow.
- Snapshot type, status, expected feeds, description, and active snapshot state.
- Command Center active snapshot panel.

## Guardrails

Snapshot management is metadata-only. It does not promote OCR output, change Operational Truth, modify historical Excel baselines, or alter exports.
