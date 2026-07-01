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

---

# Sentinel Release Notes

## v0.9.5.27 – Recoverable Gap Intelligence

### Focus

Adds an evidence-based resolver for recoverable Ground Truth gaps. The release does not change OCR output or Operational Truth. It improves the validation layer so Sentinel can distinguish rows that are truly missing from rows that are present in the export with weak identity OCR but strong unique evidence such as exact THP power.

### Added

- `parser/evidence_resolver.py` with same-server evidence resolution for Ground Truth validation.
- Unique exact-power gap recovery for rows whose identity text is weak, missing, or OCR-damaged.
- Conservative near-power recovery when supported by additional identity evidence.
- New smoke tests for evidence resolver behavior and validator gap recovery.

### Changed

- `ground_truth_validator.py` now attempts evidence-based gap recovery before falling back to blocked rank-only matches.
- Validation reports count recovered rows through existing `gap_resolved_rows` metrics using explicit `gap_*` match methods.
- Version updated to `0.9.5.27`.

### Measured impact on Server 551 Top 50 THP validation

Using the current 15-screenshot Server 551 THP export:

```text
matched_rows:           45 -> 49
recall:               0.90 -> 0.98
blocked_rank_fallbacks:  5 -> 1
gap_resolved_rows:       0 -> 4
unresolved_gap_rows:     5 -> 1
score:               66.83 -> 69.80
```

### Guardrail

Evidence recovery is validation/inference only. It does not rewrite the Sentinel export and does not override Data Guard or Ranking Guard. Operational Truth remains observed data; recovered gaps are explicit inferred validation matches.

### Validation

```text
python -m compileall -q parser ground_truth_validator.py services main.py
pytest tests/smoke/test_evidence_resolver.py tests/smoke/test_ground_truth_validator.py tests/smoke/test_validator_match_discipline.py tests/smoke/test_gap_recovery.py tests/smoke/test_gap_resolver.py tests/smoke/test_sequence_alignment.py tests/smoke/test_power_normalization.py tests/smoke/test_sentinel_ranking_guard.py tests/smoke/test_sentinel_data_guard.py tests/smoke/test_operational_import_repository.py -q
```

### Commit

```bash
git add .
git commit -m "feat(validation): resolve recoverable ground truth gaps with evidence"
git tag -a v0.9.5.27 -m "v0.9.5.27 Recoverable Gap Intelligence"
```

---

## v0.9.5.26 – Ground Truth Validation Framework

### Focus

Operationalizes the existing Ground Truth Validator for the current transfer-phase import workflow. The validator now measures the v0.9.5.25 export against curated Server 551 Top 50 THP truth and includes Ranking Guard quarantine evidence in the quality report.

### Added

- Server-scoped validation metrics so precision is calculated against the relevant Ground Truth server instead of all THP sheets in a multi-server export.
- Ranking Guard quarantine loader for `REVIEW_ranking_guard_quarantine` sheets.
- Failure classification for matched rows, blocked rank fallbacks, missing export rows, unresolved mismatches, and Ranking Guard quarantine hits.
- Failure summary sheet in the Excel validation report and `failure_summary` in the JSON report.
- Default validation paths for the current operational workflow:
  - `ground_truth/S6/server_551/top50_THP.xlsx`
  - `output/lastwar_export.xlsx`

### Changed

- `ground_truth_validator.py` can now be run directly after `python main.py` without requiring explicit paths when the standard project layout is used.
- Validation summary now exposes `validation_server`, `ocr_scope_rows`, `ocr_total_rows`, quarantine counts, Ground Truth rows found in quarantine, and export-extra rows.
- Version updated to `0.9.5.26`.

### Validation

```text
python -m compileall -q ground_truth_validator.py parser tests/smoke/test_ground_truth_validator.py
pytest tests/smoke/test_ground_truth_validator.py tests/smoke/test_sentinel_data_guard.py tests/smoke/test_operational_import_repository.py tests/smoke/test_sentinel_ranking_guard.py -q
```

### Commit

```bash
git add .
git commit -m "feat(validation): operationalize ground truth quality framework for v0.9.5.26"
git tag -a v0.9.5.26 -m "v0.9.5.26 Ground Truth Validation Framework"
```

---

This file consolidates the release notes that were previously split across many individual release-note files in `/docs`.


## v0.9.5.25 – Sentinel Ranking Guard

### Focus

Introduces the first runtime Ranking Guard as a modular Data Guard component. The release prevents silent ranking-type contamination by validating whether parsed rows semantically fit their assigned ranking type before merge/export.

### Added

- `parser/ranking_guard.py` with row-level semantic ranking-type checks.
- `REVIEW_ranking_guard_quarantine` export sheet for rows that do not fit the assigned ranking type.
- Ranking Guard metadata on quarantined rows:
  - `original_ranking_type`
  - `expected_ranking_type`
  - `ranking_guard_status`
  - `ranking_guard_confidence`
  - `ranking_guard_reason`
  - `ranking_guard_warning`
- Import report review items for Ranking Guard quarantine.
- Smoke tests covering THP rows inside Alliance Power, Alliance Power rows inside THP, valid THP pass-through, and import report visibility.
- `docs/SENTINEL_DATA_GUARD.md` documenting the Data Guard doctrine and its modular long-term model.

### Changed

- `main.py` now applies Ranking Guard after row grouping and before server content reconciliation, merge, and export.
- `parser/excel.py` exports Ranking Guard quarantine sheets with review fields.
- `services/import_repository.py` treats Ranking Guard quarantine as explicit review work.
- `version.py` updated to `0.9.5.25`.

### Guardrail

The Ranking Guard does not guess or auto-correct ranking types. Suspicious rows are quarantined with evidence and expected semantic fit.

### Validation

```text
python -m compileall -q parser services main.py
pytest tests/smoke/test_sentinel_ranking_guard.py tests/smoke/test_sentinel_data_guard.py tests/smoke/test_operational_import_repository.py -q
```

### Commit

```bash
git add .
git commit -m "feat(data-quality): add Sentinel Ranking Guard for v0.9.5.25"
git tag -a v0.9.5.25 -m "v0.9.5.25 Sentinel Ranking Guard"
```

---

## v0.9.5.28 – Inference Engine Core

### Focus

Introduces Sentinel's first read-only Inference Layer. The Context Engine operates above Operational Truth and produces explicit validation inferences from trusted neighboring evidence without changing OCR output, parser rows, exports, Data Guard decisions, or Ranking Guard decisions.

### Added

- `inference/` package.
- Context Engine for bounded local ranking gaps.
- Explainable inference metadata in Ground Truth validation details.
- `benchmarks/inference_report.json` and `benchmarks/inference_report.xlsx`.
- Smoke tests for contextual inference.

### Changed

- Ground Truth validation distinguishes observed matches from inferred conclusions.
- Single-row bounded gaps can be resolved as `inference_context_gap` when trusted neighbor anchors and power continuity provide sufficient evidence.
- Validation summary includes `inference_rows` and `inference_accepted_rows`.
- Version updated to `0.9.5.28`.

### Guardrail

Inference is read-only. Operational Truth remains protected by Data Guard and Ranking Guard. Inference reports derived conclusions; it does not fabricate runtime data.

### Commit

```bash
git add .
git commit -m "feat(inference): introduce read-only context engine for v0.9.5.28"
git tag -a v0.9.5.28 -m "v0.9.5.28 Inference Engine Core"
```

---


## v0.9.5.31 – Mobile Ranking Type Integrity Hotfix

### Focus

Fixes the Server 552 blind-test issue where German mobile Alliance Power screenshots were classified as unknown, then value-range fallback misclassified low-rank Alliance Power rows as Total Hero Power.

### Fixed

- Added localized German ranking-title evidence for mobile screenshots.
- Preserved Alliance Power source classification for low-rank alliance rows below 1B.
- Prevented Alliance Power rows from contaminating Total Hero Power exports when the source screen title is available.

### Validation

```text
10 passed
```


## v0.9.5.36 – Ranking Power Monotonicity Guard

### Focus

Generalizes the THP Power Sanity Guard into a ranking-wide power envelope guard.

### Fixed

- Prevents Alliance Power OCR spikes such as `23B -> 79B` from being promoted to top ranks.
- Keeps legitimate low-power alliance tail ranks below 1B intact.
- Preserves THP outlier quarantine behavior from v0.9.5.35.

### Added

- `parser/ranking_power_sanity_guard.py`.
- Local power-envelope validation for `alliance_power` and `total_hero_power`.
- Explainable quarantine metadata for power sanity outliers.

### Validation

```text
19 passed
```


## v0.9.5.37 – Screenshot-Aware Ranking Power Guard

### Focus

Turns the Ranking Power Guard from a strict local median filter into a rank-aware context validator.

### Fixed

- Legitimate top-3 Alliance Power rows are no longer quarantined when mobile screenshots split the top ranks across adjacent captures.
- Lower-rank Alliance Power OCR explosions remain quarantined before power sorting.
- THP Power Sanity behavior remains unchanged.

### Validation

```text
21 passed
```

## v0.9.5.24 – Documentation Consolidation

### Focus

Consolidates Sentinel documentation after the Command Center, Sentinel Data Guard, and Sentinel Data Quality Loop sprints. No runtime parser behavior is changed in this release.

### Added

- `docs/ROAD_TO_V1.md` with milestones from the current operational platform toward v1.0.0.
- `docs/MODUS_OPERANDI.md` describing the working model between the Proud Owner and Mimir.
- Updated operational documentation for Sentinel Data Guard, the Data Quality Loop, quarantine, and upcoming Ranking Guard work.

### Changed

- Consolidated historical release notes into this single `docs/RELEASE_NOTES.md`.
- Updated `docs/PROJECT_STATUS.md`, `docs/ROADMAP.md`, `docs/ARCHITECTURE.md`, `docs/README.md`, `docs/SENTINEL.md`, `docs/VISION.md`, and `docs/INTELLIGENCE.md` to reflect the current v0.9.5.23 platform state and the planned v0.9.5.25 Ranking Guard.
- Updated `version.py` to `0.9.5.24`.

### Validation

Documentation-only sprint. Expected validation:

```text
python -m compileall -q .
python main.py
python -m uvicorn sentinel:app --reload --host 127.0.0.1 --port 8010
```

### Commit

```bash
git add .
git commit -m "docs(platform): consolidate Sentinel documentation for v0.9.5.24"
git tag -a v0.9.5.24 -m "v0.9.5.24 Documentation Consolidation"
```

---

# Historical Release Notes

## Source: `RELEASE_NOTES_PATCH10A3.md`

# Patch 10A.3 - Multilingual OCR Foundation

## Purpose

Prepare Sentinel's S6 pre-transfer baseline import for multilingual player names.

Reliable Intelligence begins with reliable data.

## Added

- Configurable OCR language list
- Default multilingual OCR profile:
  - English
  - Simplified Chinese
  - Traditional Chinese
  - Japanese
  - Korean
- Environment override via `SENTINEL_OCR_LANGUAGES`
- GPU override via `SENTINEL_OCR_GPU`
- English fallback if multilingual EasyOCR initialization fails
- Smoke test for OCR language configuration

## Changed

- Removed hardcoded `easyocr.Reader(["en"])`
- OCR import is now lazy so non-OCR tests do not require EasyOCR to be installed

## Operational Instructions

After rollout:

1. Run a full reimport of all S6 pre-transfer screenshots.
2. Do not use incremental import for the baseline.
3. Compare UNKNOWN/REVIEW rates against the previous export.
4. Verify that alliance tags still parse correctly.
5. Freeze the pre-transfer baseline only after review.

## Git

```bash
git add .
git commit -m "feat(ocr): add multilingual OCR foundation"
git tag -a v0.9.4-pre-ocr-multilingual -m "Sentinel v0.9.4-pre - Multilingual OCR Foundation"
git push origin main
git push origin v0.9.4-pre-ocr-multilingual
```

The Sentinel approves.

---

## Source: `RELEASE_NOTES_PATCH10A4.md`

# Patch 10A.4 - Transfer Baseline Integrity Gate

## Purpose

Strengthen the S6 Pre-Transfer import pipeline by preventing silent ranking and server metadata errors.

## Added

- Configurable multilingual OCR foundation.
- Screenshot-level Warzone consensus validation.
- OCR rank extraction from ranking rows.
- Separate `ocr_rank` and `computed_rank` fields.
- Rank integrity warnings for missing or shifted rows.
- Export columns for rank and server quality review.

## Fixed

- Ranking rows are no longer silently renumbered as `n+1` without preserving OCR rank.
- Missing OCR rows can now be detected through rank gaps and rank mismatch warnings.
- Warzone/server detection can now require multiple matching OCR observations before automatic assignment.

## Quality Gates

- A screenshot should only be considered final when Warzone consensus is strong enough or explicitly reviewed.
- Rank gaps are surfaced in the export instead of being hidden by recomputed ranks.
- Player identity quality remains review-first rather than silently accepting weak OCR names.

## Tests

- Multilingual OCR configuration test.
- Ranking integrity validation test.
- Warzone consensus validation test.
- Existing player ranking parser test.
- Existing transfer baseline quality gate test.
- Existing ranking type fallback test.
- Existing OCR normalization test.

## Follow-up

Run a complete reimport of the S6 Pre-Transfer screenshots and inspect:

- `ocr_rank`
- `computed_rank`
- `rank_warning`
- `detected_server`
- `server_confidence`
- `server_warning`
- `server_detections`

Reliable Intelligence begins with reliable data.

---

## Source: `RELEASE_NOTES_PATCH10A5.md`

# Patch 10A.5 - EasyOCR Compatibility Hotfix

## Problem
EasyOCR does not allow `ch_tra` together with `ch_sim`, `ja` or `ko` in one Reader.
The previous multilingual configuration attempted to initialize all languages in
one Reader and failed at startup.

## Fix
- Split multilingual OCR into EasyOCR-compatible language groups.
- Use separate readers for Chinese simplified, Chinese traditional, Japanese and Korean.
- Merge OCR observations into one result stream.
- Deduplicate overlapping OCR regions by confidence.

## Default Groups
- `en + ch_sim`
- `en + ch_tra`
- `en + ja`
- `en + ko`

## Result
The OCR pipeline can process multilingual screenshots without violating EasyOCR
language compatibility rules.

---

## Source: `RELEASE_NOTES_PATCH10A6.md`

# Sentinel v0.9.4-pre – Patch 10A.6

## Transfer Baseline OCR Stability Hotfix

This patch stabilizes the S6 pre-transfer import after multilingual OCR caused metadata detection regressions and crashes.

## Added

- Separate metadata OCR path using stable English-only OCR.
- Configurable OCR profiles:
  - `fast` profile for normal CPU baseline imports.
  - `full` profile for targeted multilingual review.
- Screenshot-level Warzone consensus validation.
- Server review handling when Warzone cannot be validated.
- OCR rank preservation with separate `ocr_rank` and `computed_rank`.
- Rank integrity warnings for missing ranks and OCR/computed-rank mismatch.
- Server quality metadata in Excel export.

## Fixed

- Prevents crashes when `server=None`.
- Prevents multilingual OCR noise from breaking Warzone detection.
- Prevents missing OCR rows from being silently hidden by `n+1` rank assignment.

## Operational Notes

Default runtime profile is now `fast`:

```bash
python main.py
```

For targeted slow review with all supported language groups:

```bash
set SENTINEL_OCR_PROFILE=full
python main.py
```

## Git

```bash
git add .
git commit -m "fix(data-quality): stabilize OCR metadata and rank integrity"
git tag -a v0.9.4-pre-ocr-stability -m "Sentinel v0.9.4-pre - OCR Metadata Stability Hotfix"
git push origin main
git push origin v0.9.4-pre-ocr-stability
```

## Sentinel Principle

Reliable Intelligence begins with reliable data.

---

## Source: `RELEASE_NOTES_PATCH9.md`

# Sentinel v0.9.3 – Patch 9: First Real Intelligence

## Capability

Alliance Stability

## New Intelligence

Sentinel can now detect **Alliance Collapse Risk** from explainable evidence.

The assessment is produced from deterministic signals such as:

- collapse-risk reasoning hypotheses
- structural instability hypotheses
- low Structural Health
- weakened Whale Density
- reduced Activity
- whale departure facts
- leadership or officer departure facts
- power, member and activity decline facts

## Architecture

The generic Assessment Engine remains unchanged.

Domain knowledge lives inside the Alliance Stability capability. The default assessment rule registry now uses the capability-provided `AllianceCollapseRiskRule` while preserving the existing public rule name.

## Quality

Validated by automated tests:

- Alliance Collapse Risk detected from combined evidence
- No assessment emitted without sufficient evidence
- Collapse risk can be detected without a prior hypothesis when facts and indicators are strong enough
- Assessments remain immutable
- Recruitment Window regression tests still pass
- Assessment Engine smoke tests still pass

## Wolf Checklist

🐺 Alliance Collapse Rule implemented
🐺 Evidence aggregation implemented
🐺 Confidence deterministically calculated
🐺 Assessment generated
🐺 Assessment Engine unchanged
🐺 Unit tests passed
🐺 Regression tests passed
🐺 ZIP package created
🐺 Release candidate ready

──────────────────────────────────────────────

        The Sentinel approves.

──────────────────────────────────────────────

---

## Source: `RELEASE_NOTES_v0.9.5.10.md`

# Sentinel v0.9.5.10 – Power-First Ranking Reconstruction

## Added

- Power-first ranking reconstruction rule for THP exports.
- Ground Truth validation now prefers exact THP power matches before rank matches.

## Changed

- Exported `rank` is now the computed power-order rank.
- OCR rank remains available as `ocr_rank` evidence and produces warnings when it differs from the power-order rank.
- Rank warnings now distinguish OCR-rank mismatch from final computed rank.

## Why

Ground Truth validation showed that OCR rank tokens can be shifted or duplicated. THP values are much more stable and uniquely identify visible ranking rows. Sentinel therefore treats power as the primary reconstruction anchor and rank as supporting evidence.

---

## Source: `RELEASE_NOTES_v0.9.5.11.md`

# Sentinel v0.9.5.11 – Column Reconstruction Engine

## Added

- `parser/columns.py` with token-level column reconstruction for THP ranking rows.
- Column-aware extraction for `rank | alliance | player_name | power` after row alignment.
- Repair for malformed alliance tags such as `IPbC]` → `[PbC]`.
- Badge/noise filtering for OCR fragments before the alliance column.
- Column correction metadata exported through parser rows.
- Smoke tests for column reconstruction edge cases.

## Changed

- `parse_ranking_rows()` now delegates row-internal field extraction to the Column Reconstruction Engine.
- Player ranking builder preserves column-level corrections in parse corrections.

## Why

Power-first reconstruction improved row matching. The next bottleneck was field extraction inside each row: badge noise, malformed alliance brackets, and combined tag/name OCR tokens. This release separates row detection from column interpretation so future identity normalization can operate on cleaner structured fields.

---

## Source: `RELEASE_NOTES_v0.9.5.12.md`

# Sentinel v0.9.5.12 - Alliance Normalization

## Added

- `parser/alliance_normalization.py`
- Vocabulary-aware alliance tag normalization.
- Conservative fuzzy correction for common OCR drops such as `PBC -> PC`, `IVE -> IV`, `PWW -> PW`.
- Ground Truth Validator now reports exact vs normalized alliance matches.

## Changed

- Player ranking export normalizes alliance tags using the local snapshot vocabulary.
- Ground Truth validation uses normalized alliance matches for identity usability.

## Why

The Ground Truth report showed many otherwise usable player rows failing because OCR dropped one character from short alliance tags. This patch treats alliance tags as entities with local context instead of raw OCR strings.

---

## Source: `RELEASE_NOTES_v0.9.5.13.md`

# Sentinel v0.9.5.13 - Player Name Normalization

## Added

- Player name normalization layer for OCR-derived ranking rows.
- Latin-core extraction for mixed Latin/CJK player names.
- OCR-confusion-aware comparison keys for identity validation.
- Ground Truth Validator metrics for normalized name similarity and normalized name matches.

## Changed

- `usable_identity_match` now considers both raw name similarity and normalized name similarity.
- Validation report now exposes normalized comparison artifacts:
  - `expected_name_latin_core`
  - `ocr_name_latin_core`
  - `expected_name_key`
  - `ocr_name_key`
  - `name_normalized_match`
  - `name_normalized_similarity`

## Impact

Against the Server 551 Top 50 Ground Truth dataset:

- Score improved from `56.71` to `60.54`.
- Usable identities improved from `21` to `23`.
- Normalized name matches added: `24`.

## Notes

The raw OCR name remains unchanged. Normalization is a derived validation and identity-comparison layer, not a destructive rewrite of player names.

---

## Source: `RELEASE_NOTES_v0.9.5.14.md`

# Sentinel v0.9.5.14 - Sequence Alignment & Power Recovery

## Goal

Reduce shifted ranking-block errors by treating THP values as recoverable sequence anchors instead of isolated row fields.

## Added

- `parser/power_normalization.py`
  - exact THP comparison
  - near THP comparison
  - truncated digit recovery (`x10`)
  - bounded zero-insertion recovery
  - explainable `PowerMatchResult`

- `parser/sequence_alignment.py`
  - sequence-aware candidate scoring
  - power + name + alliance + rank evidence fusion
  - conservative recovered-power matching
  - protection against recovered-power false positives without name evidence

## Changed

- Ground Truth Validator now prefers sequence-aware matching before rank fallback.
- Validator report now includes:
  - `ocr_power_recovered`
  - `power_exact_match`
  - `power_recovered_match`
  - `power_match_type`
  - `power_similarity`
  - `sequence_alignment_score`

## Measured Impact on Server 551 Ground Truth

- Score: `60.54 -> 62.59`
- Power matches: `33 -> 36`
- Usable identities: `23 -> 26`
- Recovered power matches: `4`

## Notes

This release intentionally keeps recovered power conservative. Recovered THP can only override rank-based fallback when the player name still provides strong supporting evidence.

---

## Source: `RELEASE_NOTES_v0.9.5.17.md`

# Sentinel v0.9.5.17 – Gap Resolver

## Focus
Active resolution of recoverable validation gaps caused by screenshot/server bucket leakage.

## Added
- `parser/gap_resolver.py`
- Cross-server gap candidate search for rows exported under the wrong server sheet
- Conservative evidence scoring using power, normalized name, and alliance compatibility
- `gap_resolved_rows` validation metric
- Smoke tests for gap resolver and validator integration

## Improved
- Recoverable gaps are no longer just annotated; high-confidence candidates can now be pulled back into the correct Ground Truth row.
- Wrong rank fallbacks remain blocked unless strong evidence exists.

## Server 551 Benchmark
- Valid matches: 36 → 43
- Bad matches: 13 → 6
- Gap rows: 14 → 7
- Gap resolved rows: 7
- Precision: 0.7500 → 0.8958
- Recall: 0.7200 → 0.8600
- F1: 0.7347 → 0.8775
- Usable identities: 26 → 32
- Score: 53.69 → 63.45

---

## Source: `RELEASE_NOTES_v0.9.5.19.md`

# Sentinel v0.9.5.19 – Operational Foundation / Command Center Commit 2

## Summary

Commit 2 gives Sentinel its first user-facing Command Center shell.

The goal is not strategic intelligence yet. The goal is to establish the product surface that later hosts imports, data quality, review queues and intelligence modules.

## Added

- Command Center application service
- Command Center view models
- `/` Command Center start page
- `/command` alias
- User-facing Command Center navigation
- Operational Readiness mission panel
- Immediate Attention section
- Operational metric cards
- System Health cards
- Recent Operations log
- Import, Data Quality, Players and Reports placeholder routes

## Changed

- Root route now opens the Sentinel Command Center instead of the legacy feed.
- Intelligence feed moved to `/feed`.
- Navigation language now follows the Command Center product model.
- Templates remain presentation-only; Command Center data is prepared in the application service.

## Verified

- `python -m compileall application web sentinel.py`
- FastAPI TestClient checks:
  - `/`
  - `/command`
  - `/health`
  - `/status`
  - `/imports`
  - `/quality`
  - `/feed`
  - `/players`
  - `/reports`

## Notes

This commit intentionally uses deterministic placeholder data. Repository-backed import, quality and review data belong to the next commit.

---

## Source: `RELEASE_NOTES_v0.9.5.19_COMMIT3.md`

# Sentinel v0.9.5.19 Commit 3 - Live Data Integration

## Added

- Data Quality application service reading `benchmarks/ground_truth_validation_report.json`
- Live Command Center metrics from validator output
- Real review items from unresolved gaps and blocked rank fallbacks
- Import Center page backed by validation report evidence
- Data Quality page with server coverage and review queue
- API endpoints:
  - `/api/quality`
  - `/api/imports`

## Changed

- Command Center no longer relies exclusively on placeholder data when a validation report exists.
- Operational readiness is derived from latest F1 score.
- Immediate Attention displays real review actions.

## Notes

The repository database remains untouched in this commit. The goal is to connect the Command Center to the latest validated operational evidence first, then move persistent import history behind repositories in a later commit.

---

## Source: `RELEASE_NOTES_v0.9.5.2.md`

# Sentinel v0.9.5.2 - OCR Provider Architecture Stabilization

## Fixed

- Stabilized the OCR provider architecture by replacing slotted dataclasses with plain provider classes.
- Fixed EasyOCR provider initialization error: `EasyOcrProvider object has no attribute 'profile'`.
- Fixed PaddleOCR provider initialization error: `PaddleOcrProvider object has no attribute '_metadata_language'`.
- Kept the provider interface unchanged so benchmark and main pipeline calls remain stable.

## Rationale

The OCR providers hold runtime state such as loaded readers, selected profiles and resolved language metadata. These values are created during initialization and should be normal instance attributes. The previous slotted dataclass implementation blocked attaching those attributes and caused both benchmark providers to fail before OCR could run.

## Validation

- Provider factory smoke tests pass.
- Benchmark metrics tests pass.
- Python compilation passes for OCR provider modules and benchmark runner.

## Git

```bash
git add .
git commit -m "fix(ocr): stabilize provider architecture initialization"
git tag -a v0.9.5.2 -m "Sentinel v0.9.5.2 - OCR Provider Architecture Stabilization"
git push origin main
git push origin v0.9.5.2
```

---

## Source: `RELEASE_NOTES_v0.9.5.20.md`

# Sentinel v0.9.5.20 - Architecture Consolidation

## Added

- `application/data_quality/repository.py` repository protocol for operational quality reports.
- `services/quality_repository.py` compatibility repository adapter for latest quality report ingestion.

## Changed

- `DataQualityService` now consumes a repository boundary instead of reading validator output directly.
- Command Center now depends on application models and services only.
- User-facing text no longer exposes ground-truth report paths as runtime concepts.

## Architecture

Ground Truth is now treated as a development and benchmark concern.
Runtime data flows through:

```text
Command Center
  -> Application Service
  -> Quality Repository
  -> Operational data source
```

The current JSON adapter remains as a compatibility bridge. It can later be replaced by SQLite or PostgreSQL without changing UI routes or templates.

## Validation

- `DataQualityService` loads existing quality reports through the repository adapter.
- `CommandCenterService` renders the same live operational model as before.
- `compileall` passed for `application`, `services`, and `web`.

---

## Source: `RELEASE_NOTES_v0.9.5.21.md`

# Sentinel v0.9.5.21 – Sentinel Data Guard

## Summary

This release introduces **Sentinel Data Guard – Phase 1** and moves the Command Center toward operational runtime truth.

The main fix addresses the class of bugs where screenshots with visible row-level `Warzone #551` evidence could be exported into a wrong server sheet such as `552_total_hero_power`.

## Added

- `parser/data_guard.py`
  - `resolve_server_assignment()`
  - row-level Warzone majority evidence
  - server assignment conflict detection
  - explainable assignment decision model
- `services/import_repository.py`
  - latest operational import report writer/reader
  - runtime report persisted to `data/latest_import_report.json`
- `application/operational_import/`
  - operational import models
  - import dashboard service
- Smoke tests for Data Guard and operational import reports.

## Changed

- `main.py` now runs server assignment through Sentinel Data Guard.
- Repeated row-level Warzone evidence overrides conflicting metadata/session assignment.
- `main.py` writes an operational import report after each export.
- Command Center prefers latest import runtime data when available.
- Import Center now displays the latest import run instead of validation-derived sheet data.
- Export includes `data_guard_conflict` where available.
- Version updated to `0.9.5.21`.

## Fixed

- Prevents a visible `Warzone #551` screenshot block from silently being exported as server `552` when row-level evidence strongly supports `551`.

## Validation

```text
pytest tests/smoke/test_sentinel_data_guard.py tests/smoke/test_operational_import_repository.py -q
4 passed
```

## Principle

```text
Warzone evidence wins.
The Command Center shows the latest operational truth.
```

---

## Source: `RELEASE_NOTES_v0.9.5.22.md`

# Sentinel v0.9.5.22 – Data Guard Hotfix

## Focus

Rebuilt the Data Guard hotfix to avoid filename and timestamp-based server assignment decisions.

## Fixed

- Prevents isolated misassigned server blocks such as `551` rows exported as `552_total_hero_power`.
- Reassigns suspicious small server groups back into the stronger same-ranking server group using screenshot content evidence only.
- Marks reassigned rows with `data_guard_conflict=True` and `server_assignment_conflict` warning details.

## Data Guard Evidence Policy

Decision evidence is content-first:

1. Warzone / OCR content
2. Parsed ranking row content
3. Power continuity
4. Alliance tag overlap
5. Row count and confidence

Filename patterns and screenshot filename timestamps are not used for server assignment decisions.

## Validation

- Sentinel Data Guard smoke tests: `4 passed`
- Simulated against the latest 549/550/551 import export:
  - `552_total_hero_power` is removed
  - `551_total_hero_power` increases from `72` to `86` rows
  - reassigned rows are marked as Data Guard conflicts

---

## Source: `RELEASE_NOTES_v0.9.5.23.md`

# Sentinel v0.9.5.23 – Sentinel Data Quality Loop

## Focus

Introduces the first Sentinel Data Quality Loop and changes Data Guard content reconciliation from unsafe auto-merge to safe quarantine.

## Added

- `parser/quality_loop.py`
- Targeted OCR recovery attempts for uncertain server assignments.
- Content-based preprocessing strategies:
  - header crop
  - CLAHE contrast enhancement
  - 2x/3x upscale
  - unsharp mask
  - adaptive threshold
- Recovery attempt metadata for explainability.
- Data Guard quarantine path for suspicious isolated server blocks.

## Changed

- Data Guard no longer silently merges suspicious low-confidence server blocks into another server.
- Suspicious isolated blocks are moved to `REVIEW_data_guard_quarantine` instead.
- Import reports now include quarantine reviews and Data Quality Loop checks.
- Version updated to `0.9.5.23`.

## Guardrail

The Data Quality Loop does not use filename or timestamp logic for server decisions.

Data Guard validates and protects.  
The Data Quality Loop tries to recover better OCR evidence.  
If evidence remains insufficient, Sentinel quarantines the block for human review.

## Validation

```text
python -m compileall -q parser services main.py
pytest tests/smoke/test_sentinel_data_guard.py tests/smoke/test_operational_import_repository.py -q
6 passed
```

Full smoke collection still contains pre-existing invalid legacy smoke files unrelated to this patch.

---

## Source: `RELEASE_NOTES_v0.9.5.3.md`

# Sentinel v0.9.5.3 - OCR Benchmark Finalization Hotfix

## Fixed

- Fixed Windows console Unicode crashes when printing OCR names containing Asian characters.
- Added UTF-8 stdout/stderr configuration with safe fallback printing.
- Updated PaddleOCR provider for PaddleOCR 3.x API changes.
- Removed dependency on legacy `ocr(..., cls=False)` calls.
- Added flexible PaddleOCR result normalization for v3 result objects and legacy v2 list outputs.

## Goal

The benchmark should now complete far enough to produce actual EasyOCR and PaddleOCR quality metrics instead of failing on provider/runtime compatibility issues.

## Engineering Principle

Reliable engineering begins with measurable results.

---

## Source: `RELEASE_NOTES_v0.9.5.4.md`

# Sentinel v0.9.5.4 - Benchmark Subprocess Encoding Hotfix

## Fixed

- Benchmark subprocess output is now decoded as UTF-8 with replacement fallback.
- Windows cp1252 decode crashes no longer stop the benchmark runner.
- Missing stdout/stderr values are handled safely.
- Provider logs are written with UTF-8 replacement fallback.

## Purpose

This hotfix ensures benchmark infrastructure survives OCR output containing Asian characters or provider logs with non-cp1252 bytes.

---

## Source: `RELEASE_NOTES_v0.9.5.5.md`

# Sentinel v0.9.5.5 – EasyOCR Baseline Calibration

## Purpose

Calibrate the EasyOCR transfer-baseline pipeline after the first real benchmark.
The goal is to reduce false REVIEW noise while keeping genuinely unsafe rows in review.

## Changed

- Added calibrated player identity quality parser.
- Prefix noise before `[TAG]` is now treated as a correction, not an automatic review.
- CJK player names are accepted as valid when OCR returns usable characters.
- Missing alliance tags are recorded as warnings but no longer automatically invalidate a row.
- Missing OCR rank no longer creates a `rank_warning` for every row.
- Rank warnings now focus on actual OCR evidence: rank mismatches and observed rank gaps.
- Warzone consensus with at least three matching detections no longer propagates row-level server warnings.

## Why

The previous pipeline was too conservative:

- 100% of THP rows were REVIEW.
- Every row received a rank warning when OCR rank was missing.
- Accepted server consensus still created many server warnings.

This patch makes the quality gate actionable instead of noisy.

## Expected Result

After re-running EasyOCR:

- VALID rows should appear again.
- REVIEW rows should represent truly problematic identities.
- Rank warnings should highlight real integrity issues instead of design noise.
- Server warnings should be reserved for screenshots that actually require attention.

The Sentinel approves.

---

## Source: `RELEASE_NOTES_v0.9.5.6.md`

# Sentinel v0.9.5.6 - Ground Truth Validation Framework

## Added

- `ground_truth_validator.py`
- Ground Truth Excel comparison
- Name accuracy metrics
- Alliance accuracy metrics
- Power and rank accuracy metrics
- Usable identity match metric
- Name category breakdown for Latin/CJK/mixed names
- JSON and Excel validation reports
- Documentation: `docs/GROUND_TRUTH_VALIDATION.md`

## Purpose

This release adds the first objective OCR quality measurement against manually
curated truth data. It allows Sentinel to measure whether OCR output is good
enough for Player Identity and later Player Mobility.

## Run

```bash
python ground_truth_validator.py --ground-truth input/S6_preTransfer_server_551_top50_THP.xlsx --ocr-output output/easy_lastwar_export.xlsx
```

The Sentinel approves.

---

## Source: `RELEASE_NOTES_v0.9.5.7.md`

# Sentinel v0.9.5.7 – Ground Truth Validator Import Hotfix

## Fixed

- Ground Truth Validator no longer requires an explicit `server` column in OCR exports.
- Server is derived from THP sheet names such as `551_total_hero_power` when missing.
- Duplicate OCR name columns are collapsed safely.
- OCR exports with `ocr_name`, `player_name`, or `name` variants are handled robustly.
- Alliance/tag aliases are normalized before validation.

## Command

```bash
python ground_truth_validator.py --ground-truth input/S6_preTransfer_server_551_top50_THP.xlsx --ocr-output output/easy_lastwar_export.xlsx
```

---

## Source: `RELEASE_NOTES_v0.9.5.8.md`

# Sentinel v0.9.5.8 - Ground Truth Validator Duplicate Column Hotfix

## Fixed

- Ground Truth Validator no longer crashes when OCR Excel exports contain duplicate `ocr_name` columns.
- Duplicate Excel columns are collapsed before validation.
- Scalar normalization now tolerates pandas Series/DataFrame values defensively.
- Validator can now compare Server 551 Ground Truth against the OCR export successfully.

## Verification

Command tested:

```bash
python ground_truth_validator.py --ground-truth input/S6_preTransfer_server_551_top50_THP.xlsx --ocr-output output/easy_lastwar_export.xlsx
```

Result on provided Server 551 dataset:

- Ground Truth rows: 50
- Matched rows: 44
- Missing rows: 6
- Name exact matches: 2
- Average name similarity: 0.2953
- Alliance matches: 12
- Power matches: 13
- Rank matches: 34
- Usable identity matches: 4
- Score: 34.13

---

## Source: `RELEASE_NOTES_v0.9.5.9.md`

# Sentinel v0.9.5.9 – Row Alignment Engine

## Added

- Bounding-box based row alignment engine in `parser/alignment.py`.
- Layout-aware THP row reconstruction using power values as row anchors.
- Rank-token pairing by nearest Y position.
- Row bands based on neighbouring power anchors.
- Alignment warnings for missing rank anchors and empty reconstructed names.
- Smoke tests for row-shift prevention.

## Changed

- `parse_ranking_rows()` no longer relies on broad OCR text clustering as the primary parser strategy.
- Parsed rows preserve visual order before final merge/debugging.
- Existing ranking merge keeps alignment warnings in `rank_warning` so suspicious rows remain visible in Excel.

## Rationale

Ground-truth validation for Server 551 showed that low name accuracy was largely caused by row reconstruction drift rather than pure OCR failure. The new alignment engine treats OCR output as positioned layout evidence first and text second.

## Expected Impact

- Fewer cases where one player's name is assigned to the next player's power.
- Better name, alliance, and power consistency against ground truth.
- Cleaner foundation for future identity matching and Joiner/Leaver detection.

---

## Source: `RELEASE_NOTES_v0.9.5.md`

# Sentinel v0.9.5 - OCR Benchmark Framework

## Added

- Pluggable OCR provider architecture
- EasyOCR provider
- PaddleOCR provider
- OCR provider factory
- Benchmark runner: `benchmark_ocr.py`
- Runtime and quality benchmark metrics
- Benchmark Excel and JSON reports
- OCR provider documentation
- OCR benchmark documentation
- Engineering principles documentation

## Changed

- `parser/ocr.py` now delegates to an OCR provider instead of instantiating EasyOCR directly.
- `main.py` supports provider-selected output files through `SENTINEL_OUTPUT_FILE`.
- `main.py` prints selected OCR provider and runtime summary.

## Quality

- Existing parser and quality gates remain the benchmark constant.
- Only OCR provider changes between benchmark runs.

## Usage

```bash
python benchmark_ocr.py
```

or

```bash
python benchmark_ocr.py --providers easy,paddle
```

## Git

```bash
git add .
git commit -m "feat(ocr): add OCR benchmark framework"
git tag -a v0.9.5 -m "Sentinel v0.9.5 - OCR Benchmark Framework"
git push origin main
git push origin v0.9.5
```

The Sentinel approves.

---

## Source: `RELEASE_NOTS_v0.9.5.1.md`

# Sentinel v0.9.5.1 - OCR Benchmark Hotfix

## Fixed

- Removed incompatible `show_log=False` argument from PaddleOCR initialization.
- Added constructor fallback for newer PaddleOCR versions.
- Sanitized benchmark rows before writing Excel reports.
- Removed ANSI/control characters that caused `openpyxl.IllegalCharacterError`.

## Validation

- `python -m py_compile benchmark_ocr.py ocr/paddleocr_provider.py ocr/provider.py ocr/provider_factory.py ocr/utils.py`

## Run

```bash
python benchmark_ocr.py
```

If PaddleOCR is installed correctly, the benchmark now writes:

- `benchmarks/ocr_benchmark_report.json`
- `benchmarks/ocr_benchmark_report.xlsx`
- `benchmarks/easy_run.log`
- `benchmarks/paddle_run.log`

---

