# Sentinel Patch Summary

Consolidated patch history for the Sentinel v0.9.5.x stabilization line. Future patches should update this document instead of creating standalone root-level patch summary files.

---

<!-- Source: PATCH_SUMMARY_v0.9.5.48.md -->

# Sentinel v0.9.5.48 Patch Summary

## Release

v0.9.5.48 – Source Context Recovery Reportability

## Focus

Expose context-aware power candidate scoring in operational outputs and fix import-report review-count aggregation.

## Key changes

- Added power candidate recovery metadata columns to Excel exports.
- Added top-level `power_recovery` candidate traces to `data/latest_import_report.json`.
- Added per-import recovery counters.
- Added direct row metadata for best candidate, second candidate, margin, status, confidence, and reason.
- Fixed global `review_count` aggregation so it no longer reports zero while import blocks report review warnings.
- Updated documentation and version to v0.9.5.48.

## Validation

```bash
python -m compileall -q parser services main.py version.py
pytest tests/smoke/test_ranking_power_sanity_guard.py tests/smoke/test_operational_import_repository.py tests/smoke/test_sentinel_ranking_guard.py tests/smoke/test_ranking_recovery.py -q
```

Observed:

```text
23 passed
```

## Commit

```bash
git add .
git commit -m "feat(reporting): expose power candidate recovery traces"
git tag -a v0.9.5.48 -m "v0.9.5.48 Source Context Recovery Reportability"
```

---

<!-- Source: PATCH_SUMMARY_v0.9.5.49.md -->

# Sentinel v0.9.5.49 – Candidate Decision Engine Cutover

## Focus

Out with the old: removes the legacy leading-digit power recovery fallback from the decision path.

In with the new: recovered power values are selected only by the context candidate decision engine when the best candidate has a clear score and margin.

## Changed

- Removed `legacy_leading_digit_recovery` as a recovery decision fallback.
- Keeps leading-digit variants only as generated candidates.
- Recovers only when candidate scoring produces a clear winner.
- Quarantines ambiguous candidate ties instead of silently recovering.
- Adds decision audit metadata:
  - `power_recovery_decision_strategy`,
  - `power_recovery_decision_version`,
  - `power_recovery_legacy_used`.

## Updated

- `parser/ranking_power_sanity_guard.py`
- `services/import_repository.py`
- `parser/excel.py`
- `tests/smoke/test_ranking_power_sanity_guard.py`
- `tests/smoke/test_operational_import_repository.py`
- `version.py`
- Sentinel documentation under `/docs`

## Validation

```text
python -m compileall -q parser services main.py version.py
pytest tests/smoke/test_ranking_power_sanity_guard.py tests/smoke/test_operational_import_repository.py tests/smoke/test_sentinel_ranking_guard.py tests/smoke/test_ranking_recovery.py -q
23 passed
```

## Commit

```bash
git add .
git commit -m "fix(recovery): remove legacy power recovery fallback"
git tag -a v0.9.5.49 -m "v0.9.5.49 Candidate Decision Engine Cutover"
```

---

<!-- Source: PATCH_SUMMARY_v0.9.5.50.md -->

# Sentinel v0.9.5.50 – Bidirectional Power Error Model

## Focus

Adds an OCR power error model to the candidate decision engine introduced in v0.9.5.49.

v0.9.5.49 made high power explosion handling safe by removing legacy fallback decisions. v0.9.5.50 extends the same margin-gated recovery model to low/truncated THP values observed in the Server 549–553 regression run.

## Added

- Low/truncated THP candidate generation:
  - `scale_x10_truncated_digit`,
  - `scale_x100_truncated_digit`,
  - `insert_zero`.
- OCR error model scoring for high THP leading-digit explosions:
  - `leading_digit_to_1`,
  - `leading_digit_to_2`,
  - `leading_digit_to_3`.
- Regression tests for:
  - high THP explosion recovery,
  - low THP truncation recovery,
  - Alliance Power low-tail protection.

## Guardrails

- Recovery remains source-local.
- Recovery remains margin-gated.
- Ambiguous candidates still quarantine.
- Runtime does not use Ground Truth.
- Alliance Power low tails are not treated as THP truncation errors.

## Validation

```text
python -m compileall -q parser main.py ground_truth_validator.py sentinel.py version.py
pytest tests/smoke/test_ranking_power_sanity_guard.py tests/smoke/test_thp_power_sanity_guard.py tests/smoke/test_sentinel_ranking_guard.py tests/smoke/test_ranking_recovery.py tests/smoke/test_operational_import_repository.py -q
30 passed
```

## Commit

```bash
git add .
git commit -m "feat(recovery): add bidirectional OCR power error model"
git tag -a v0.9.5.50 -m "v0.9.5.50 Bidirectional Power Error Model"
```

---

<!-- Source: PATCH_SUMMARY_v0.9.5.51.md -->

# Sentinel v0.9.5.51 Patch Summary – Digit-Preserving Power Recovery

## Focus

Hardens the v0.9.5.50 bidirectional OCR power error model with explicit digit-preservation scoring for low/truncated THP recovery candidates.

## Why

The Server 549–553 regression run showed that v0.9.5.50 recovered many low-truncated THP rows, but some candidate choices were still too numerical-context-driven. A candidate can fit the local power envelope while distorting the visible OCR digit sequence.

## Changed

- Added `digit_preservation_score` to `PowerRecoveryCandidate`.
- Added candidate metadata export via `power_recovery_candidates`.
- Added candidate reason traces such as `digit_preservation:0.840`.
- Added a digit-preserving low-truncation decision path for narrow but strong candidate margins.
- Kept high explosion and Alliance Power decisions margin-gated.
- Updated recovery decision version to `v0.9.5.51`.
- Updated project docs, changelog, release notes, and version.

## Guardrail

Digit preservation is only a scoring signal. It does not bypass Data Guard, Ranking Guard, source-local context, or quarantine-first doctrine. Runtime still does not use Ground Truth, filename order, or upload order as truth.

## Validation

```text
python -m compileall -q parser services main.py ground_truth_validator.py sentinel.py version.py
pytest tests/smoke/test_ranking_power_sanity_guard.py tests/smoke/test_thp_power_sanity_guard.py tests/smoke/test_sentinel_ranking_guard.py tests/smoke/test_ranking_recovery.py tests/smoke/test_operational_import_repository.py -q
30 passed
```

Full `pytest tests/smoke -q` still collects pre-existing invalid/hotfix smoke files unrelated to this sprint.

## Commit

```bash
git add .
git commit -m "feat(recovery): add digit-preserving power candidate scoring"
git tag -a v0.9.5.51 -m "v0.9.5.51 Digit-Preserving Power Recovery"
```

---

<!-- Source: PATCH_SUMMARY_v0.9.5.52.md -->

# Sentinel v0.9.5.52 Patch Summary – Segment Order Recovery Guardrails

## Focus

v0.9.5.52 moves recovery hardening from raw power scoring into segment integrity. It keeps the bidirectional/digit-preserving candidate engine, adds a conservative segment-order tie-break for close high-explosion THP candidates, and quarantines low-truncation ties that remain ambiguous.

## Changed

- Added segment-order tie-break helper functions.
- High 7xxM THP candidates may recover an order-consistent near-tie candidate.
- Low/truncated THP recovery now requires stronger margin/digit evidence across multi-candidate cases.
- Updated recovery decision version to `v0.9.5.52`.
- Updated `/docs` release notes, changelog, architecture, project status, data guard notes, and lessons learned.

## Validation

```text
pytest tests/smoke/test_ranking_power_sanity_guard.py tests/smoke/test_operational_import_repository.py tests/smoke/test_ground_truth_validator.py tests/smoke/test_inference_context_engine.py tests/smoke/test_sentinel_data_guard.py -q
31 passed
```

## Commit

```bash
git add .
git commit -m "fix(recovery): add segment-order guardrails for power candidates"
git tag -a v0.9.5.52 -m "v0.9.5.52 Segment Order Recovery Guardrails"
```

---

<!-- Source: PATCH_SUMMARY_v0.9.5.53.md -->

# Sentinel v0.9.5.53 Patch Summary

## Title
Adaptive Review OCR Pipeline

## Purpose
v0.9.5.52 stabilized power recovery and segment-order guardrails, but the remaining 549–553 review rows showed that many failures are crop/image/row-OCR quality issues rather than additional power-scoring problems. v0.9.5.53 turns review into a controlled second-pass OCR stage.

## Changes
- Added `parser/review_ocr.py`.
- Added adaptive row-local Review OCR after Ranking/Power Guard and before final reconciliation.
- Preserved `visual_y` in player ranking legacy rows so questionable rows can be cropped from the source screenshot.
- Added deterministic review variants: row crop, tall/shifted crops, 2x zoom, CLAHE, and sharpen.
- Added conservative promotion gate: weak or ambiguous review OCR remains quarantine.
- Added `review_ocr_*` metadata to Excel exports and import reports.
- Added top-level `review_ocr` summary to `data/latest_import_report.json`.
- Updated `/docs`, including `LESSONS_LEARNED.md`.
- Added regression tests for adaptive review OCR.

## Validation
```text
pytest tests/smoke/test_adaptive_review_ocr.py tests/smoke/test_operational_import_repository.py tests/smoke/test_ranking_power_sanity_guard.py -q
23 passed

python -m compileall -q parser services models main.py
passed
```

Note: full-repository compile still hits pre-existing invalid legacy files (`analysis/alliance.py`, `analytics/services/ranking_service.py`, old smoke command stubs). These are unchanged by this patch.

## Commit
```bash
git add .
git commit -m "feat(review): add adaptive review OCR pipeline"
git tag -a v0.9.5.53 -m "v0.9.5.53 Adaptive Review OCR Pipeline"
```

---

<!-- Source: PATCH_SUMMARY_v0.9.5.54.md -->

# Sentinel v0.9.5.54 Patch Summary

## Name

Contextual Row Reconstruction

## Summary

Adds a conservative second review remediation layer after Adaptive Review OCR. Low/truncated THP review rows may be promoted only when a digit-preserving candidate fits between trusted source-local anchors from the same screenshot.

## Validation

```text
31 passed
compileall parser/services/main/version/ground_truth_validator passed
```

## Commit

```bash
git add .
git commit -m "feat(review): add contextual row reconstruction"
git tag -a v0.9.5.54 -m "v0.9.5.54 Contextual Row Reconstruction"
```

---

<!-- Source: PATCH_SUMMARY_v0.9.5.55.md -->

# Sentinel v0.9.5.55 Patch Summary

## Sprint

Command Center MVP

## Added

- `services/command_center.py`
- Automatic generation of:
  - `output/command_center.html`
  - `output/review_dashboard.html`
- Smoke test: `tests/smoke/test_command_center.py`

## Changed

- `main.py` now renders dashboards after saving `data/latest_import_report.json`.
- `version.py` updated to `0.9.5.55`.
- `/docs` updated for release notes, changelog, roadmap, project status, and lessons learned.

## Guardrail

The Command Center is report-only. It does not duplicate OCR, Data Guard, Ranking Guard, Recovery, or quarantine logic.

## Validation

```text
pytest tests/smoke/test_command_center.py -q
1 passed
python -m compileall -q services/command_center.py main.py version.py
```

## Commit

```bash
git add .
git commit -m "feat(ui): add command center dashboard"
git tag -a v0.9.5.55 -m "v0.9.5.55 Command Center MVP"
```

---

<!-- Source: PATCH_SUMMARY_v0.9.5.56.md -->

# Sentinel v0.9.5.56 Patch Summary

## Focus

Review Quality Sprint: add a focused Review Evidence Pack instead of expanding the Command Center with more broad telemetry.

## Added

- `output/review_evidence_pack.html` generated after each run.
- `output/review_evidence_pack.json` generated after each run.
- Review evidence cards with:
  - server / ranking / rank
  - screenshot reference
  - original and selected power
  - best and second candidate
  - margin and decision reason
  - Review OCR and Row Reconstruction status
  - suggested human action
  - expandable candidate details
- Command Center artifact links to the Evidence Pack.
- Smoke test coverage for Evidence Pack generation.

## Changed

- `main.py` prints the Evidence Pack output path.
- `version.py` updated to `0.9.5.56`.
- `/docs` updated: CHANGELOG, RELEASE_NOTES, PROJECT_STATUS, ROADMAP, LESSONS_LEARNED.

## Guardrails

- Evidence Pack is report-driven and read-only.
- It does not promote rows.
- It does not alter OCR, recovery, Data Guard, Ranking Guard, quarantine, or export decisions.

## Validation

```text
python -m compileall -q services/command_center.py main.py version.py
pytest tests/smoke/test_command_center.py -q
1 passed
```

## Commit

```bash
git add .
git commit -m "feat(review): add review evidence pack"
git tag -a v0.9.5.56 -m "v0.9.5.56 Review Evidence Pack"
```

---

<!-- Source: PATCH_SUMMARY_v0.9.5.57.md -->

# Sentinel v0.9.5.57 Patch Summary

## Sprint
Evidence Trace Binding

## Baseline
Sentinel_v0.9.56.zip

## Changes
- Bound Review Evidence Pack items to matching `power_recovery.traces` using exact matching and conservative screenshot-local fallback.
- Added fallback support for synthetic `ranking_guard_quarantine` traces when review rows expose expected ranking types.
- Added trace status, source file, candidate count, candidate reasons, and digit-preservation score to evidence cards.
- Added direct review-table links from Command Center / Review Dashboard to evidence-card anchors.
- Updated version to 0.9.5.57.
- Updated docs in `/docs`, including CHANGELOG, RELEASE_NOTES, PROJECT_STATUS, ROADMAP, and LESSONS_LEARNED.

## Validation
```text
pytest tests/smoke/test_command_center.py -q
2 passed
python -m compileall -q services/command_center.py main.py version.py
```

## Guardrail
Evidence Trace Binding is read-only. It improves explainability only and does not promote rows, resolve reviews, or alter Operational Truth.

---

<!-- Source: PATCH_SUMMARY_v0.9.5.58.md -->

# Sentinel v0.9.5.58 Patch Summary

## Theme
Human Review Guidance and Review History Foundation.

## Changes
- Added human-facing problem statements to Review Evidence Pack items.
- Added candidate choice lists: Vorschlag 1/2/3 plus manual input.
- Added problem type/label and confidence label metadata to evidence JSON.
- Added persistent `data/review_history.json` and mirrored `output/review_history.json`.
- Updated docs and version to 0.9.5.58.

## Validation
- `pytest tests/smoke/test_command_center.py -q`
- `python -m compileall services/command_center.py main.py version.py`

---

<!-- Source: PATCH_SUMMARY_v0.9.5.59.md -->

# Sentinel v0.9.5.59 Patch Summary

## Review UX & Explainability Foundation

This sprint turns review output from a technical quarantine list into a human-readable review workflow foundation.

### Added
- Integrated `review_center.html` as the future human-in-the-loop workspace.
- Open review cards with explicit problem statements, choices, and explainability trace.
- Review history table inside the Review Center.
- `why_bullets` and `explainability_steps` in review evidence payloads.
- Resolution template fields prepared for later interactive review handling.

### Preserved
- `review_evidence_pack.html` remains available as a legacy/static evidence view.
- No OCR, Data Guard, Ranking Guard, or export decision logic was changed.
- Operational Truth remains protected; review pages are read-only.

### Validation
- `pytest tests/smoke/test_command_center.py -q` → 3 passed.
- `compileall services/command_center.py main.py version.py` → passed.

---

<!-- Source: PATCH_SUMMARY_v0.9.5.60.md -->

# Sentinel v0.9.5.60 Patch Summary

## Title
Command Center Consolidation & Review History Dedupe

## Purpose
v0.9.5.60 consolidates Sentinel's review/navigation structure and fixes persistent review history duplication. The sprint keeps OCR and recovery logic unchanged and focuses on the operator workflow around imports, quality, reviews, and evidence.

## Changes
- Added stable review identity keys independent of runtime timestamps.
- Review history now updates existing open reviews via `last_seen_at` and `seen_count` instead of creating duplicate open records on reruns.
- Existing duplicated v0.9.5.59 history is normalized and collapsed on the next Command Center generation.
- Added `/reviews` web route as the unified Review Center entry point.
- Added `web/templates/reviews.html` with open reviews, history, and static evidence links.
- Mounted `output/` as `/static-output` for current run-detail HTML during consolidation.
- Updated navigation language around Command Center, Imports, Quality, Reviews, and Operations.
- Static HTML labels now treat Evidence Pack as review detail/evidence rather than a competing Command Center.
- Updated version to `0.9.5.60`.

## Validation
- `pytest tests/smoke/test_command_center.py`
- `python -m compileall services/command_center.py web/app.py web/routes/reviews.py version.py`

## Commit
```bash
git add .
git commit -m "feat(ui): consolidate review center navigation"
git tag -a v0.9.5.60 -m "v0.9.5.60 Command Center Consolidation"
```

---

<!-- Source: PATCH_SUMMARY_v0.9.5.61.md -->

# Sentinel v0.9.5.61 Patch Summary

## Sprint
Interactive Review Resolution Foundation

## Added
- Web Review Center can mark persistent review-history items as `RESOLVED`.
- Resolution form supports candidate selection, manual power value, manual name, manual alliance, reviewer, and comment.
- Resolved reviews can be reopened from the Review Center.
- Review history counts are recalculated after resolve/reopen actions.
- Smoke test coverage for resolve/reopen helper logic.

## Changed
- Review Center now displays open and resolved review sections.
- Static Review Center text clarifies that static HTML remains read-only run-detail evidence.
- Version updated to `0.9.5.61`.

## Guardrail
Manual resolution is audit state only. It does not change OCR evidence, quarantine, Operational Truth, or Excel exports.

## Validation
```text
pytest tests/smoke/test_command_center.py -q
python -m compileall -q services/command_center.py web/app.py web/routes/reviews.py version.py
```

---

<!-- Source: PATCH_SUMMARY_v0.9.5.62.md -->

# Sentinel v0.9.5.62 Patch Summary

## Sprint
Visible Navigation Consolidation

## Added

- Persistent Command Center workflow bar across web pages: Command, Imports, Quality, Reviews, Exports.
- Expanded readable sidebar with grouped navigation, descriptions, and consistent product language.
- Review detail route `/reviews/{history_key}`.
- Review detail template showing problem statement, choices, resolution form, why-bullets, and explainability trace.
- Cross-link panels on Command Center, Imports, and Quality pages.
- Shared CSS for workflow navigation, link cards, review detail cards, trace cards, and resolution forms.
- Smoke test coverage for navigation model, templates, cross-links, and review detail route registration.

## Changed

- Review evidence is now accessible through the web application, not only through `output/review_evidence_pack.html`.
- The visible UI now matches the target operator flow: Command Center -> Imports -> Quality -> Reviews -> Exports.
- Version updated to `0.9.5.62`.

## Guardrail

No OCR, Data Guard, Ranking Guard, recovery, quarantine, Operational Truth, or Excel export behavior was changed.

## Validation

```text
pytest tests/smoke/test_web_navigation_consolidation.py tests/smoke/test_command_center.py -q
9 passed
python -m compileall -q web/app.py web/navigation.py web/routes web/templates version.py
```

## Commit

```bash
git add .
git commit -m "feat(ui): expose command center workflow navigation"
git tag -a v0.9.5.62 -m "v0.9.5.62 Visible Navigation Consolidation"
```

---

<!-- Source: PATCH_SUMMARY_v0.9.5.63.md -->

# Sentinel v0.9.5.63 Patch Summary

## Sprint
Human Review Screenshot Evidence

## Changes
- Added `/screenshots` static route for source screenshot evidence.
- Review Detail now renders screenshot filename as an open-in-new-tab link.
- Review Detail now includes a screenshot preview panel that opens the original screenshot.
- Review Queue screenshot references are clickable.
- Added CSS for screenshot evidence panels matching the Command Center style.
- Added smoke tests for screenshot links, preview markup, safe URL generation, and static mount.
- Updated docs and version metadata.

## Validation
```text
pytest tests/smoke/test_web_navigation_consolidation.py tests/smoke/test_command_center.py
python -m compileall web/app.py web/navigation.py web/routes web/templates services/command_center.py version.py
```

## Commit
```bash
git add .
git commit -m "fix(review): link screenshot evidence from review detail"
git tag -a v0.9.5.63 -m "v0.9.5.63 Human Review Screenshot Evidence"
```

---

<!-- Source: PATCH_SUMMARY_v0.9.5.64.md -->

# Sentinel v0.9.5.64 Patch Summary

## Release

v0.9.5.64 – Review Evidence Highlight Overlay

## Focus

Makes screenshot evidence usable inside Review Detail by reducing the preview footprint, switching to a two-column reviewer workspace, and highlighting the target rank directly on the screenshot preview. Also consolidates historical patch summaries into `/docs/PATCH_SUMMARY.md`.

## Key changes

- Added rank highlight overlay metadata for review detail items.
- Added compact screenshot evidence column with sticky preview.
- Added target-rank overlay and badge on screenshot previews.
- Kept full-resolution screenshot links opening in a new tab.
- Reworked Review Detail into a left decision column and right evidence column.
- Added `/docs/PATCH_SUMMARY.md` as the consolidated patch-summary register.
- Updated documentation and version to v0.9.5.64.

## Validation

```text
pytest tests/smoke/test_web_navigation_consolidation.py -q
9 passed
python -m compileall -q web/app.py web/navigation.py web/routes web/templates services/command_center.py version.py
passed
```

## Commit

```bash
git add .
git commit -m "feat(review): highlight target rank in screenshot evidence"
git tag -a v0.9.5.64 -m "v0.9.5.64 Review Evidence Highlight Overlay"
```


<!-- Source: PATCH_SUMMARY_v0.9.5.65.md -->

# Sentinel v0.9.5.65 Patch Summary

## Version

v0.9.5.65 – Screenshot Highlight Calibration

## Purpose

Calibrates the Review Detail screenshot rank overlay so the marker aligns with the first visible ranking row instead of landing too low in the screenshot preview. Improves reviewer trust by treating the overlay as a visual aid with explicit approximate-state handling.

## Changes

- Replaced the naive v0.9.5.64 rank-to-y-position heuristic with ranking-type overlay profiles.
- Calibrated `alliance_power` and `total_hero_power` first-row anchors and row spacing against current Last War screenshot geometry.
- Added highlight metadata: label and approximate flag.
- Added human-friendly dotted number formatting for review choices in Review Detail.
- Kept screenshot links opening in a new tab.
- Added smoke coverage for calibrated first-row overlay positions.
- Updated documentation and version to v0.9.5.65.

## Validation

```text
pytest tests/smoke -q
compileall web/app.py web/navigation.py web/routes web/templates services/command_center.py version.py
```

## Commit

```bash
git add .
git commit -m "fix(review): calibrate screenshot rank highlight overlay"
git tag -a v0.9.5.65 -m "v0.9.5.65 Screenshot Highlight Calibration"
```

<!-- Source: PATCH_SUMMARY_v0.9.5.66.md -->

# Sentinel v0.9.5.66 Patch Summary

## Version

v0.9.5.66 – Operational Readiness Drilldown

## Purpose

Adds a server-level Operational Readiness layer to the Command Center start page so the Proud Owner can immediately see how much of the server dataset is usable and where action is required.

## Changes

- Added Operational Readiness view models: status cards, server health items, and coverage summary.
- Added Command Center KPI cards for discovered servers, operational servers, pending reviews, missing data, and failed imports.
- Added drill-down links from KPI cards to Servers, Reviews, Quality, and Imports.
- Added a compact server health strip on the Command Center start page.
- Added drill-down banners to destination pages when filter links are used.
- Updated documentation and version to v0.9.5.66.

## Validation

```text
pytest tests/smoke/test_web_navigation_consolidation.py -q
10 passed
python -m compileall -q application/command_center web/app.py web/navigation.py web/routes web/templates services/command_center.py version.py
passed
```

Note: full `pytest tests/smoke -q` still encounters pre-existing legacy collection errors in unrelated smoke files with command-line snippets or older OCR config imports.

## Commit

```bash
git add .
git commit -m "feat(command): add operational readiness drilldown"
git tag -a v0.9.5.66 -m "v0.9.5.66 Operational Readiness Drilldown"
```
