# Release Notes

## v0.9.5.150 — Strike VII: Position-Bound Evidence Provenance

- Added a complete read-only provenance chain for every blocked Gold-Core character position.
- Traces screenshot reference, crop geometry, OCR observation, vote resolution, evidence reconstruction, and Promotion Guard outcome.
- Identifies the first failed stage and a concrete evidence-acquisition action per position.
- Added `evidence_provenance_report.json`, `evidence_provenance_report.xlsx`, and `evidence_provenance_summary.md`.
- Ground Truth remains comparison context only; UNKNOWN, conflicts, and incomplete evidence remain protected.
- No Gold-Core clearance or Operational Truth behavior changed.


## Strike VI — Position-Bound Evidence Intelligence

- Added a Gold-Core-specific Character Position Evidence Map for every remaining blocker.
- Records each expected character position as `CONFIRMED`, `MISSING`, `UNRESOLVED`, or `CONFLICT`.
- Records proof source, selected glyphs, vote status, confidence, crop diagnostics, anchor status, screenshots, and conflicts per position.
- Added `character_position_report.json`, `character_position_report.xlsx`, `character_position_summary.md`, and `position_heatmap.json`.
- Added case-level blocking-position lists and targeted evidence recommendations.
- Integrated Gold-Core character cases, positions, and heatmap into the main validation JSON and Excel reports.
- Added smoke coverage for conflict visibility and strict UNKNOWN protection.
- No Gold-Core clearance policy, Promotion Guard, Ground Truth, snapshot, export, or Operational Truth was changed.

---

# Release Notes — v0.9.5.148

## Documentation Sprint after Gold Core Zero III

- Added authoritative analysis of the v0.9.5.147 benchmark.
- Recorded that Gold Core changed from 15 to 14, with the sole clearance caused by the existing Strike-I rule.
- Recorded that Evidence Reconstruction cleared 0 cases and all 5 `vote_warning_gate_review` cases remain.
- Updated Project Status, Road to V1, Gold Core Zero Plan, Casebook, Lessons Learned, Architecture, and Modus Operandi.
- Consolidated release history into `RELEASE_NOTES.md`; deprecated duplicate loose release-note files.
- No runtime behavior or Operational Truth was changed.

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

# Release Notes

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

v0.9.5.129 executes the read-only Context Gap evidence lane introduced in v0.9.5.128. Eligible high-confidence Context Gaps now produce report-only suggested display and confidence evidence while Operational Truth remains locked.

### Added

- `read_only_reocr_executed`
- `read_only_reocr_evidence`
- `read_only_suggested_display`
- `read_only_confidence`
- `read_only_operational_truth_modified`
- Phase marker: `v0.9.5.129_read_only_verification_execution`

### Guardrails

- Evidence-only execution.
- No verified display overwrite.
- No export/snapshot/database/Ground Truth mutation.
- No promotion from contextual inference into Operational Truth.

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

Create the first dedicated Gold Core blocker triage layer. The sprint does not tune generic OCR and does not weaken DataGuard. It makes the remaining Gold Core blockers actionable by exposing each blocked row with its evidence status, failure class, fix lane, and next safe action.

### Changes

- Added `gold_core_blocker_report.json`.
- Added `gold_core_blocker_report.xlsx`.
- Added `gold_core_summary` and `gold_core_blockers` sheets to the main validation workbook.
- Added `gold_core_blocker_summary` and `gold_core_blockers` sections to `ground_truth_validation_report.json`.
- Added diagnostic classes: `local_glyph_solvable`, `mixed_local_and_nonlocal_blocker`, `policy_nonlocal_script_display`, `crop_geometry_problem`, `observed_text_confirmed`, `vote_warning_gate_review`, `context_gap_read_only`, and `manual_review`.
- Added smoke tests for Gold Core blocker report classification.

### Validation

```text
pytest -q tests/smoke/test_gold_core_blocker_report_126.py tests/smoke/test_gold_blocker_triage_113.py tests/smoke/test_gold_gate_cleanup_114.py
6 passed
py_compile OK
```

### Commit / Tag

```bash
git add .
git commit -m "feat(gold-core): add blocker triage report for v0.9.5.126"
git tag -a v0.9.5.126 -m "v0.9.5.126 Gold Core Blocker Triage"
```

---


## v0.9.5.125 – Documentation Consolidation & Handover

This sprint consolidates Sentinel project knowledge after the Gold Fidelity Engine Phase 1 milestone. It is a documentation-first release: no OCR, matching, DataGuard, ReOCR, cache, inference, or Operational Truth logic is intentionally changed.

### Changed

- Consolidated scattered release notes into `docs/RELEASE_NOTES.md`.
- Consolidated scattered patch summaries into `docs/PATCH_SUMMARY.md`.
- Updated `PROJECT_STATUS.md` to reflect the current v0.9.5.124 validation state:
  - 50/50 matched rows on the 551 benchmark;
  - 0 missing rows;
  - 0 bad matches;
  - 100% recall;
  - 32 verified core identity matches;
  - 15 remaining Gold Core blockers;
  - runtime reduced to roughly 8 minutes in the latest observed validator run;
  - row integrity score improved to 66%.
- Updated `ROAD_TO_V1.md` with the next milestones through v1.0.0.
- Updated `LESSONS_LEARNED.md`, `MODUS_OPERANDI.md`, `SENTINEL_DATA_GUARD.md`, `ARCHITECTURE.md`, and `NEXT_CHAT.md` for a clean handover.
- Added `ARCHITECTURE_HISTORY.md` to explain why the architecture evolved from OCR tuning toward evidence-first data stability.
- Added `VERSIONING_POLICY.md` to capture release and commit conventions.
- Archived legacy loose release-note and patch-summary files under `docs/archive/` after consolidation.
- Added `docs/RELEASE_NOTED.md` as a compatibility pointer to the canonical `docs/RELEASE_NOTES.md` because the handover request used both spellings.

### Validation

```text
Documentation files updated
python -m py_compile version.py OK
zip integrity OK
```

### Commit / Tag

```bash
git add .
git commit -m "docs(project): consolidate handover documentation for v0.9.5.125"
git tag -a v0.9.5.125 -m "v0.9.5.125 Documentation Consolidation and Handover"
```


# Consolidated Historical Release Notes

## v0.9.5.124 – Gold Fidelity Engine Phase 1

- Adds a snapshot-local Character ReOCR Evidence Cache for exact target/text pairs. Decisive `verified_expected` / `verified_observed` glyph outcomes can be reused inside the same validation run without re-reading the same crop class repeatedly.
- Cached evidence is explicitly marked with `reason=evidence_cache_hit` and `crop_strategy=snapshot_evidence_cache`; it does not claim a fresh crop read and does not modify Operational Truth.
- Keeps cache scope conservative: field, target position, expected glyph, observed glyph, reason, expected field text, and observed field text must all match. No historical player database or cross-snapshot identity memory is used.
- Adds cache counters into validator detail rows: `reocr_evidence_cache_hits`, `reocr_evidence_cache_misses`, `reocr_evidence_cache_writes`, and `reocr_evidence_cache_saved_reocr`.
- Extends smoke coverage for cache keys, cacheable outcomes, and cached-evidence provenance.

Validation:

```text
focused smoke tests passed
py_compile OK for changed modules
zip integrity OK
```

```bash
git add .
git commit -m "perf(gold-fidelity): cache reusable reocr evidence"
git tag -a v0.9.5.124 -m "v0.9.5.124 Gold Fidelity Engine Phase 1"
```

## v0.9.5.123 – Evidence Triage and ReOCR Stop Rules

- Adds a stricter pre-ReOCR Core Safety Gate for already stable Latin residual and script-limited identities.
- Skips low-yield player-name glyph probes when Core Identity is already provably stable before ReOCR, while keeping true repair cases such as `Joncollins21` eligible.
- Separates policy skips from missing evidence: nonlocal/multilingual targets now become `not_requested_policy_nonlocal` and row integrity reports classify them as `ROW_OK_POLICY_NONLOCAL` or `ROW_POLICY_NONLOCAL_REVIEW` instead of collapsing everything into `ROW_EVIDENCE_MISSING`.
- Adds a soft per-target ReOCR timeout to stop one bad glyph target from dominating CPU-only validation runtime.
- Keeps Full Gold strict and does not promote display fidelity without exact/screenshot-supported evidence.

Validation:

```text
53 focused smoke tests passed
py_compile OK for changed modules
zip integrity OK
```

```bash
git add .
git commit -m "perf(data-guard): triage evidence and stop low-yield reocr"
git tag -a v0.9.5.123 -m "v0.9.5.123 Evidence Triage and ReOCR Stop Rules"
```

## v0.9.5.122 – ReOCR Budget Gate and Crop Hygiene

- Adds a conservative ReOCR budget gate for harmless alliance tag case-only probes such as `PbC` vs `PBC` when rank/power/name-core evidence is already stable. Full display Gold remains strict; this only avoids spending CPU on low-yield proof.
- Separates Core Alliance equivalence from exact display fidelity: normalized/current-snapshot alliance matches can support Core Identity, while `verified_alliance_display_exact_match` still requires exact or screenshot-proven display evidence.
- Reclassifies crop/power-column bleed and outside-allowed-set votes as `ROW_OK_WITH_*_WARNING` when Core Identity is already verified, so Evidence Inspector review effort focuses on real blockers.
- Emits `character_reocr_budget_skipped` and `character_reocr_budget_gate_reasons` in validator detail rows for auditability.

```bash
git add .
git commit -m "perf(data-guard): gate low-yield reocr and classify crop warnings"
git tag -a v0.9.5.122 -m "v0.9.5.122 ReOCR Budget Gate and Crop Hygiene"
```

## v0.9.5.121

- Planning sprint for Evidence-first improvements.
- Added roadmap for Crop Geometry Inspector, Row Alignment Heatmap, Evidence Timeline and Fragment Voting Visualizer.
- No functional code changes in this documentation handover sprint.


## v0.9.5.121 – OCR Evidence Inspector and Row Integrity Diagnostics

- Adds OCR Evidence Inspector output to the Ground Truth Validator.
- Writes `ocr_evidence_report.json` and `ocr_evidence_report.xlsx`.
- Adds row-level integrity diagnostics for accepted rows, contextual gaps, unresolved ReOCR, observed-text confirmations, and crop/field mismatch evidence.
- Preserves fragment provenance from Character ReOCR: screenshot, row slot, crop box, target field, selected glyph, crop strategy, anchor status, diagnostic, and vote text.
- Keeps matching, inference, ReOCR voting, DataGuard, Ranking Guard, and Operational Truth unchanged. This is evidence-first diagnostics, not identity auto-resolution.

Validation: 12 focused smoke tests passed.

## v0.9.5.117 – Reconstruction Candidate Gate

- Gates expensive Latin Name Block Reconstruction to residual high-confidence Latin-only player-name blockers.
- Skips block reconstruction when cheaper glyph ReOCR already verified all local player-name targets.
- Keeps DATAGUARD conservative: no UNKNOWN, mixed CJK/Hangul/Kana, nonlocal target, weak alignment, power-mismatch, or alliance-mismatch expansion.
- Preserves v0.9.5.116 quality path while reducing unnecessary OCR work on already-solved names such as Joncollins21 and Tragedy122280.

## v0.9.5.112 – Verified Display Evidence Apply Hotfix

v0.9.5.111 introduced verified-display fields, but the validator counted evidence through a legacy `item.target.field` lookup. The active `CharacterVerificationEvidence` stores the field directly as `item.field`, so rows such as `Joncollinszl`/`PBC` still showed raw OCR values in `verified_name_display` and `verified_alliance_display` even though all local glyphs were `verified_expected`.

### Fixed

- Count Character ReOCR evidence from the direct `field` attribute.
- Apply fully verified local glyph evidence into `verified_name_display` and `verified_alliance_display`.
- Preserve the conservative block for skipped/nonlocal glyph drift; CJK/Hangul display drift is still not silently promoted.

### Validation

```text
pytest tests/smoke/test_verified_display_112.py tests/smoke/test_glyph_verification_109.py tests/smoke/test_alliance_tag_glyph_110.py
py_compile OK for changed validator module
zip integrity OK
```

### Commit

```bash
git add .
git commit -m "fix(data-guard): count verified display evidence from direct fields"
git tag -a v0.9.5.112 -m "v0.9.5.112 Verified Display Evidence Apply Hotfix"
```

## v0.9.5.111 – Verified Display Resolution

v0.9.5.110 proved the missing piece for `[PbC]`/`PBC`: the full-tag-block anchor can verify the expected case-sensitive tag from the current screenshot. v0.9.5.111 turns those ReOCR proofs into validator-visible resolved display identity instead of leaving them only in debug evidence.

### Changed
- Added verified-display fields for player name and alliance tag (`verified_name_display`, `verified_alliance_display`).
- Added verified exact identity metrics that count rows where OCR display drift is fully resolved by Character ReOCR evidence.
- Gold-Fidelity blockers now use verified display identity, not only raw OCR display identity.
- Kept conservative behavior: skipped/nonlocal glyph drift cannot become gold automatically.
- Added smoke coverage for the verified-display resolution gate.

### Why it matters
Joncollins-style first-contact rows no longer stop at “debug says the expected glyphs were seen.” If all local drift targets are verified, the validator can now treat `Joncollinszl / PBC` as screenshot-proven `Joncollins21 / PbC` for fidelity scoring without depending on historical player memory.

### Commit / Tag
```bash
git add .
git commit -m "feat(data-guard): apply verified display resolution to gold fidelity"
git tag -a v0.9.5.111 -m "v0.9.5.111 Verified Display Resolution"
```

## v0.9.5.110 – Alliance Tag Glyph Block Anchor

v0.9.5.109 reduced unnecessary Character ReOCR from broad/nonlocal drift and proved that player-name glyphs such as `Joncollins21` can be verified screenshot-locally. The remaining blocker is alliance-tag fidelity, especially case-sensitive tags such as `PbC` being exported as `PBC`. v0.9.5.110 changes tag verification from single-glyph-first to full-tag-block-first. Sentinel now tries to read the complete short tag block (`[TAG]` / `TAG`) before falling back to individual glyph probes.

### Implemented

- Added full alliance-tag block anchor candidates before noisy single-glyph tag crops.
- Preserved screenshot-local verification: no historical player database and no manual identity lookup.
- Improved `[PbC]`/`PBC` case-sensitive verification by selecting the target glyph from the complete tag block when available.
- Kept the v0.9.5.109 local-glyph gate and `character_reocr_skipped_nonlocal` behavior unchanged.
- Added regression tests for tag-block candidate ordering and `[PbC]` case verification.

### Validation

```bash
pytest -q tests/smoke/test_alliance_tag_glyph_110.py tests/smoke/test_glyph_verification_109.py tests/smoke/test_targeted_character_reocr_geometry_106.py tests/smoke/test_character_reocr_103.py
python -m py_compile ground_truth_validator.py parser/targeted_character_reocr.py
```

### Commit

```bash
git add .
git commit -m "fix(data-guard): anchor alliance tag glyph verification on full tag blocks"
git tag -a v0.9.5.110 -m "v0.9.5.110 Alliance Tag Glyph Block Anchor"
```

## v0.9.5.109 – Glyph Verification Engine Gate

v0.9.5.108 proved that telemetry works and showed the next architectural issue: Character ReOCR was spending large CPU time on broad display drift that local glyph verification cannot safely solve. v0.9.5.109 changes the validator from “re-read every visible difference” to “re-read only true local glyph ambiguities”. This keeps the solution independent of historical player databases and focused on the current screenshot.

### Changed
- Added a local glyph target filter before Character ReOCR.
- Keeps high-value confusable cases such as `Joncollinszl` → `Joncollins21` (`z/2`, `l/1`) and case-sensitive alliance tags such as `PbC` → `PBC`.
- Skips non-local broad drift such as Hangul/CJK replacement spans, UNKNOWN-expanded names, and insertion/deletion tails that cannot be proven by a single glyph crop.
- Adds `character_reocr_skipped_nonlocal` to validation summary, category summary, failure summary, and JSON reports.
- Keeps DataGuard conservative: skipped non-local drift remains a Gold Fidelity blocker; it is not auto-corrected and not silently accepted as exact identity.

### Intent
Sentinel must not depend on historical identity memory to read first-contact screenshots from the 549–676 transfer bucket or the broader 2000+ server universe. The path to V1 is therefore local proof: correct row, correct field, correct glyph. v0.9.5.109 narrows the expensive glyph verifier to the subset where that local proof is realistic.

### Validation
```text
pytest -q tests/smoke/test_glyph_verification_109.py tests/smoke/test_targeted_character_reocr_geometry_106.py tests/smoke/test_character_reocr_debug_102.py
python -m py_compile ground_truth_validator.py parser/targeted_character_reocr.py
zip integrity OK
```

### Commit
```bash
git add .
git commit -m "feat(data-guard): gate reocr to local glyph verification"
git tag -a v0.9.5.109 -m "v0.9.5.109 Glyph Verification Engine Gate"
```

## v0.9.5.108 – Runtime JSON Serialization Hotfix

v0.9.5.107 correctly added runtime telemetry, but the first long CPU-only validator run exposed a report-writing bug: pandas/numpy scalar values such as `int64` could enter `runtime_debug_report.json` through fields like `slowest_target_rank`. The validation itself could complete, but the process crashed while serializing the runtime report.

Changes:
- Adds a JSON-safe conversion layer for runtime telemetry payloads.
- Converts pandas/numpy scalars, tuples, lists, dictionaries, and NaN-like values before writing `runtime_debug_report.json`.
- Keeps runtime telemetry observational only; it does not change matching, inference, ReOCR voting, or Operational Truth.
- Preserves the `.107` alliance-tag and timing instrumentation behavior.

Validation:
```text
py_compile OK
runtime payload JSON serialization smoke OK
zip integrity OK
```

Commit:
```bash
git add .
git commit -m "fix(data-guard): serialize runtime telemetry safely"
git tag -a v0.9.5.108 -m "v0.9.5.108 Runtime Telemetry Serialization Hotfix"
```

## v0.9.5.107 – Alliance Tag Fidelity + Runtime Telemetry

v0.9.5.106 finally proved that calibrated Character ReOCR can recover the Joncollins tail digits (`2` and `1`) from screenshot evidence, but alliance-tag case fidelity remains a blocker (`PbC` still often appears as `PBC`). v0.9.5.107 keeps the conservative DataGuard posture and adds two focused improvements.

### Changed
- Added wider full-tag ReOCR candidates for alliance tags so short tags such as `[PbC]` can be read as a field before selecting the target character.
- Added per-target timing fields to Character ReOCR evidence: `target_total_ms`, `crop_generation_ms`, `variant_build_ms`, `ocr_read_ms`, and `vote_selection_ms`.
- Added `benchmarks/runtime_debug_report.json` and `benchmarks/runtime_debug_report.xlsx` to show where long Validator/ReOCR runs spend their time.
- Extended Character ReOCR debug output with the new timing columns.

### DataGuard posture
- Runtime telemetry is observational only. It does not change matching, inference, ReOCR votes, or Operational Truth.
- Gold Fidelity remains blocked unless player name, alliance tag, rank, and power are exact or character-verified.

### Commit
```bash
git add .
git commit -m "feat(data-guard): add runtime telemetry and tag crop calibration"
git tag -a v0.9.5.107 -m "v0.9.5.107 Alliance Tag Fidelity and Runtime Telemetry"
```

## v0.9.5.106 – Character Crop Calibration Harness

v0.9.5.105 proved that fixed mini-crops were too brittle: Joncollins21/PbC targets were detected correctly, but the title-line crops often produced `crop_no_text_detected` or non-target CJK noise. v0.9.5.106 keeps the DataGuard rules conservative and adds a deterministic crop-calibration harness around every targeted Character ReOCR crop.

### Changed
- Added calibrated crop candidates around the primary character crop (`base`, `left_wide`, `right_wide`, `up_wide`, and combined variants).
- Moved visible-window title-line crops slightly upward so orange commander-name glyphs are not clipped at the top.
- ReOCR now ranks candidate crops by verified expected/observed status, crop diagnostics, non-empty votes, and confidence.
- Added debug fields: `crop_candidate_index`, `crop_candidate_count`, and `crop_candidate_reason`.
- Added smoke coverage proving an empty base crop can be recovered by a calibrated fallback candidate.

### Guardrails
- ReOCR still does not modify Operational Truth.
- Expected-character verification remains required for Gold Fidelity; observed/noise votes do not auto-correct identity.
- Alignment context gaps still bypass Character ReOCR.

### Commit
```bash
git add .
git commit -m "fix(data-guard): add calibrated character crop fallback"
git tag -a v0.9.5.106 -m "v0.9.5.106 Character Crop Calibration Harness"
```

## v0.9.5.105 – Character Crop Line Focus Guard

v0.9.5.105 targets the concrete Joncollins21/PbC failure exposed by the v0.9.5.104 reports. The pipeline already detected the right row and the right high-value character targets, but the character crops still included the wrong pixels: late player-name crops hit the final/empty area or non-name text, while alliance-tag crops included neighbouring glyphs and the lower `Warzone #551` line.

### Changed

- Added a Latin-name glyph-pitch crop model for visible-window screenshots.
- Kept Joncollins-style tail-character crops on the title line and centered on the actual `2`/`1` glyphs.
- Reduced visible-window alliance-tag crops to the target glyph instead of the full tag neighborhood.
- Shortened visible-window character crops vertically to avoid the lower `Warzone #551` line.
- Added v0.9.5.105 smoke coverage for Joncollins tail digits and `[PbC]` middle-glyph crops.

### Expected validation movement

- Fewer `crop_no_text_detected` cases for late Latin-name characters.
- Fewer `crop_power_column_bleed` false diagnostics on title-line tail digits.
- Better chance that `Joncollins21 -> Joncollinszl` resolves expected `2/1` instead of staying unresolved.
- Better chance that `PbC -> PBC` verifies the case-sensitive middle `b`.

### Commit

```bash
git add .
git commit -m "fix(data-guard): focus character crops on title-line glyphs"
git tag -a v0.9.5.105 -m "v0.9.5.105 Character Crop Line Focus Guard"
```

## v0.9.5.104 – Character Geometry & Tag Fidelity Guard

v0.9.5.104 focuses on the blocker exposed by the v0.9.5.103 debug run: Character ReOCR was active, but late player-name crops could still leak into the power column and alliance-tag crops for `[PbC]`/`PBC` were too wide and too far to the right.

### Changed
- Tightened visible-window player-name crop geometry so late-name targets such as `Joncollins21` positions `2/1` stay inside the identity column instead of reading power digits.
- Tightened visible-window alliance-tag glyph crops so middle-tag case checks such as `PbC` vs `PBC` inspect the target glyph instead of the `C]`/right-bracket area.
- Added `crop_power_column_bleed` diagnostics when player-name ReOCR votes are dominated by power-like digits.
- Kept Character ReOCR evidence-only; no Operational Truth is changed from ReOCR.

### Validation
```text
9 passed – Ground Truth Validator + Character Geometry smoke tests
py_compile OK
zip integrity OK
```

### Commit
```bash
git add .
git commit -m "fix(data-guard): tighten character geometry and tag fidelity diagnostics"
git tag -a v0.9.5.104 -m "v0.9.5.104 Character Geometry and Tag Fidelity Guard"
```

## v0.9.5.103 – ReOCR Row Slot & Field Anchor Correction

v0.9.5.103 addresses the main finding from the v0.9.5.102 debug reports: Character ReOCR was often looking at the wrong vertical row or at a crop without the expected field anchor. This was visible when `[PbC]` targets sometimes read `[IVE]`, proving that the blocker was crop localization rather than raw OCR strength.

### Changed

- Added window-screenshot row geometry for 551-style screenshots around 627x915 instead of forcing the older 600x1064 normalized row pitch.
- Character ReOCR now records crop-anchor diagnostics: `crop_anchor_status`, `crop_anchor_text` and `crop_diagnostic`.
- The debug report can now distinguish `crop_field_mismatch`, `crop_no_text_detected` and `vote_outside_allowed_set` instead of only `no_votes` / `no_selected_char`.
- Alliance-tag and player-name crops remain evidence-only. No automatic identity correction is performed.

### Guardrails

- Operational Truth is unchanged.
- Alignment context gaps remain excluded from Character Verification.
- Cache behavior is untouched and remains unsuitable for data-quality validation unless explicitly requested.

### Validation

```bash
pytest -q tests/smoke/test_character_reocr_103.py tests/smoke/test_targeted_character_reocr_97.py tests/smoke/test_character_reocr_debug_102.py
python -m py_compile ground_truth_validator.py parser/targeted_character_reocr.py
```

### Commit

```bash
git add .
git commit -m "fix(data-guard): correct reocr row geometry and crop diagnostics"
git tag -a v0.9.5.103 -m "v0.9.5.103 ReOCR Row Slot and Field Anchor Correction"
```

## v0.9.5.102 – Character ReOCR Debug Instrumentation

v0.9.5.102 adds diagnostic instrumentation for the 551 Gold Fidelity sprint. After v0.9.5.101 failed to materially improve Character ReOCR validation, this patch stops guessing at crop fixes and makes the ReOCR path inspectable target by target.

### Added

- `character_reocr_debug_report.json` and `character_reocr_debug_report.xlsx` from the Ground Truth Validator.
- Flattened Character ReOCR debug rows with screenshot, row slot, crop box, crop strategy, vote variants, raw vote texts, selected glyph, confidence and final status.
- Diagnostic metadata in `CharacterVerificationEvidence`: `crop_strategy`, `text_length`, `expected_text`, `observed_text` and `allowed_chars`.
- Smoke tests for the new debug report generation.

### Guardrails

- Operational Truth is not changed.
- Character ReOCR still remains evidence-only.
- Alignment context gaps remain excluded from Character Verification.
- Cache behavior is untouched.

### Validation

```bash
pytest -q tests/smoke/test_character_reocr_debug_102.py tests/smoke/test_targeted_character_reocr_97.py tests/smoke/test_character_reocr_98.py tests/smoke/test_alignment_guard_100.py
python -m py_compile ground_truth_validator.py parser/targeted_character_reocr.py
```

### Commit

```bash
git add .
git commit -m "feat(data-guard): instrument character re-ocr debug evidence"
git tag -a v0.9.5.102 -m "v0.9.5.102 Character ReOCR Debug Instrumentation"
```

## v0.9.5.101 – Character Crop Precision Guard

v0.9.5.101 tightens targeted Character Re-OCR after v0.9.5.100 proved the Alignment Guard was working but only 2 of 8 expected glyph confirmations were observed. The main cause was crop and vote pollution: player-name crops still included alliance tags, and alliance-tag votes could select bracket/neighbor characters instead of the requested tag glyph.

### Changed

- Player-name character crops now start after the bracketed alliance tag instead of at the beginning of the identity column.
- Alliance-tag vote extraction is position-aware inside bracketed tags such as `[PbC]`.
- ReOCR votes are now conservative: only expected, observed, or explicit confusion-family characters can be selected as evidence. Off-target OCR noise becomes `unresolved`, not `ambiguous_vote`.
- Added regression tests for `[PbC]`/`[PBC]` tag position voting and off-target noise suppression.
- Updated documentation and version metadata to v0.9.5.101.

### Validation

```bash
pytest -q tests/smoke/test_targeted_character_reocr_97.py tests/smoke/test_character_reocr_98.py tests/smoke/test_alignment_guard_100.py
python -m py_compile ground_truth_validator.py parser/targeted_character_reocr.py
```

### Commit

```bash
git add .
git commit -m "fix(data-guard): tighten character re-ocr crop and vote precision"
git tag -a v0.9.5.101 -m "v0.9.5.101 Character Crop Precision Guard"
```

## v0.9.5.100 – Ground Truth Alignment Guard

v0.9.5.100 separates contextual alignment gaps from true character-fidelity drift. The previous validator path could compare a Ground Truth row against a neighbouring OCR row accepted only as read-only contextual inference, producing false character differences such as `K9 Thunder` versus `YUNS` or `HUNI` versus `Zacharys`.

### Changed

- Added an Alignment Guard after contextual inference.
- Contextual inference rows now receive `alignment_guard_status = context_gap_no_character_verification`.
- Character Verification and Character ReOCR are suppressed for `inference_context_gap` rows.
- Alignment context gaps no longer contribute to `gold_fidelity_blocker_rows` or `identity_risk_rows`.
- Reports now include `alignment_guard_summary` and `alignment_context_gaps` sections/sheets.
- Updated documentation and version metadata to v0.9.5.100.

### Validation

```bash
pytest -q tests/smoke/test_alignment_guard_100.py
python -m py_compile ground_truth_validator.py inference/context_engine.py parser/targeted_character_reocr.py
```

### Commit

```bash
git add .
git commit -m "fix(data-guard): separate alignment gaps from character verification"
git tag -a v0.9.5.100 -m "v0.9.5.100 Ground Truth Alignment Guard"
```

## v0.9.5.99 – Character Re-OCR Provider Input Fix

v0.9.5.99 fixes the runtime blocker found in v0.9.5.98 where targeted character re-OCR passed PIL image crops directly into EasyOCR. EasyOCR expects a file path, bytes or numpy array, so the validator crashed with `ValueError: Invalid input type`.

### Changed
- Convert PIL crop variants to RGB numpy arrays before calling Sentinel's EasyOCR provider.
- Keep fallback behavior conservative: if no OCR provider is available, evidence can still be emitted as unresolved rather than modifying Operational Truth.
- Version and documentation updated to v0.9.5.99.

### Validation
- `python -m py_compile ground_truth_validator.py parser/targeted_character_reocr.py`
- Targeted unit smoke with fake reader confirms PIL crops are converted and evidence is produced.
- ZIP integrity check.

### Commit
```bash
git add .
git commit -m "fix(data-guard): convert character re-ocr crops for EasyOCR"
git tag -a v0.9.5.99 -m "v0.9.5.99 Character Re-OCR Provider Input Fix"
```

## v0.9.5.99 – Character Re-OCR Provider Input Fix

v0.9.5.99 fixes the v0.9.5.97 validation gap where Character Verification candidates were counted but no targeted re-OCR targets were emitted in the standard validator run.

### Added
- Ground Truth validator now auto-discovers screenshot evidence by default.
- `--screenshots-dir` accepts both directories and ZIP files such as `551.zip`.
- Added `--no-verify-characters` for explicit opt-out.
- Character re-OCR evidence is emitted even when the OCR provider is unavailable; targets are then marked unresolved instead of silently staying at zero.
- Added regression tests proving ZIP discovery and non-zero target emission for `Joncollins21` / `Joncollinszl` and `PbC` / `PBC`.

### Validation
- 5 passed – targeted character re-OCR and ZIP discovery smoke tests.
- 551 validator smoke run against uploaded `lastwar_export.xlsx` and `551.zip` produced `character_reocr_target_count = 183` instead of 0.
- `py_compile` OK.

### Commands
```bash
git add .
git commit -m "fix(data-guard): activate character re-ocr evidence by default"
git tag -a v0.9.5.99 -m "v0.9.5.99 Character Re-OCR Provider Input Fix"
```

## v0.9.5.97 – Targeted Character Re-OCR Evidence

v0.9.5.97 turns the v0.9.5.96 Gold Fidelity blocker list into an actionable screenshot-evidence workflow. It does **not** claim Server 551 is Gold-ready yet. It adds the first conservative implementation of real targeted character re-OCR for player names and alliance tags.

### Added

- `parser/targeted_character_reocr.py`
  - Parses `character_verification_targets` generated by the Identity / Gold Fidelity validator.
  - Locates an approximate row and field crop in the original screenshot.
  - Runs multiple image variants over the crop when an OCR reader is provided.
  - Records per-character votes, selected character, confidence and status.
- `ground_truth_validator.py --verify-characters`
  - Optional mode for targeted screenshot re-OCR evidence.
  - Adds report columns:
    - `character_reocr_status`
    - `character_reocr_targets`
    - `character_reocr_verified_expected`
    - `character_reocr_verified_observed`
    - `character_reocr_unresolved`
    - `character_reocr_evidence`
    - `ground_truth_row_slot`
- Smoke tests for the targeted character re-OCR layer.

### Guardrails

- No fuzzy identity promotion.
- No automatic canonicalization such as `Joncollinszl -> Joncollins21` from context.
- No cache enablement.
- Operational Truth remains unchanged unless screenshot evidence is explicitly verified by future gates.
- Alliance tags remain case-sensitive: `PbC != PBC`, `DAY != daY`.

### How to run the new validator mode

Normal import remains unchanged:

```bash
python main.py --no-ocr-cache
```

Then run the Ground Truth validator normally:

```bash
python ground_truth_validator.py --ocr-output output\snapshots\<snapshot>\lastwar_export.xlsx
```

Optional targeted character re-OCR evidence mode:

```bash
python ground_truth_validator.py --ocr-output output\snapshots\<snapshot>\lastwar_export.xlsx --verify-characters --screenshots-dir screenshots
```

### Validation

```text
9 passed – targeted character re-OCR / character verification smoke tests
551 GT validator smoke run OK
py_compile OK
zip integrity OK
```

### Commit

```bash
git add .
git commit -m "feat(data-guard): add targeted character re-ocr evidence"
git tag -a v0.9.5.97 -m "v0.9.5.97 Targeted Character Re-OCR Evidence"
```

## v0.9.5.113 - Gold Blocker Triage

- Adds a diagnostic Gold Blocker Triage report to the Ground Truth Validator.
- Classifies remaining Gold Fidelity blockers by domain: player name, alliance tag, combined identity, rank/power, alignment, and nonlocal/multilingual drift.
- Adds `gold_blocker_triage_summary` and `gold_blocker_triage` to JSON output plus Excel sheets `gold_blocker_triage` and `gold_blocker_details`.
- Keeps matching, inference, Character ReOCR voting, DataGuard, and Operational Truth unchanged. This sprint is diagnostic, not corrective.


## v0.9.5.115 - Latin Player Name Core Resolution

- Extends the local glyph gate to handle Latin-only missing glyphs in otherwise aligned names.
- Adds safe handling for Latin spacing gaps so formatting does not block Core Identity when the compact Latin name is still locally aligned.
- Keeps mixed CJK/Hangul/Kana display drift conservative; no historical identity database or manual mapping is introduced.
- Adds smoke tests for `Mizzenmast -> Mzzenmast`, Latin spacing gaps, and mixed Unicode rejection.

## v0.9.5.114 - Player Name Drift Triage and Core Identity Gold Gate

- Added a transfer-critical Core Identity gate alongside the stricter full row Gold Fidelity gate. Core Identity means verified player display + verified alliance display + matched power/server; rank display drift is now visible as a separate full-fidelity blocker instead of being mixed with name/tag identity failures.
- Added `verified_core_identity_match`, `verified_core_identity_resolution`, `gold_core_blocker`, `verified_core_identity_matches`, `gold_core_blocker_rows`, and `gold_core_ready` to validator/detail summaries.
- Added `core_identity_summary` and `core_identity_verified_rows` to the JSON report, plus `core_identity` and `core_identity_rows` sheets in the Excel report.
- Improved Gold Blocker Triage classes to separate `identity_core_verified_rank_only_blocker`, `identity_core_verified_power_display_blocker`, multilingual/nonlocal player-name drift, and true local glyph failures.
- No Operational Truth write path changed. DataGuard, row-alignment guard, inference read-only handling, and ReOCR voting remain conservative.

Expected effect: `.114` will not magically solve CJK/Hangul player-name drift, but it will stop rank-only/full-row fidelity noise from hiding rows where transfer-critical identity is already proven.

## v0.9.5.116 – Latin Name Block Reconstruction

- Added screenshot-local Latin Name Block Reconstruction for aligned Latin-only player names where single-glyph ReOCR is too weak, e.g. missing/shifted characters such as `Mizzenmast -> Mzzenmast`, `Drpeek -> Ieek`, and spacing/digit drifts like `N E R D -> NER0`.
- Reconstruction is DATAGUARD-gated: it only runs on accepted/aligned rows, does not use historical identity data, and refuses mixed CJK/Hangul/Kana display drift.
- Added reconstruction evidence to the existing character ReOCR debug stream with crop strategy `latin_name_block`, candidate text, selected reconstruction, confidence, and timing.
- Core Identity can now accept a verified Latin name block when the whole-name OCR candidate supports the expected display more strongly than the observed OCR string.
## v0.9.5.118 – Non-Latin Identity Policy Gate

- Added a script-limited Core Identity policy for mixed Latin/CJK/Hangul names.
- Keeps Full Display Fidelity strict while allowing transfer-relevant Core Identity where Latin core, alliance, and power are stable.
- Adds JSON/Excel diagnostics for script-limited identity rows.
- Preserves DataGuard discipline: no Operational Truth mutation and no database/history dependency.

Validation: 24 focused smoke tests passed.



## v0.9.5.121 – Latin Residual Validator Crashfix

- Fixes a validator crash introduced in v0.9.5.119 where `expected_name_key` / `actual_name_key` were referenced before initialization.
- Keeps Latin Residual Core behavior unchanged.
- No OCR, policy, or Operational Truth behavior changes.

## v0.9.5.119 – Latin Residual Core Blocker Cleanup

- Added a conservative Latin-only residual Core Identity policy for remaining rows where the stable expected Latin core is visibly contained in the OCR result despite OCR prefix/suffix garbage or display spacing noise.
- New fields: `latin_residual_core_identity_match`, `latin_residual_core_identity_resolution`, and `latin_residual_policy_reason`.
- New report sections and Excel sheets: `latin_residual_policy_summary`, `latin_residual_policy_rows`, `latin_residual_policy`, and `latin_residual_rows`.
- Keeps Full Display Fidelity strict: Latin residual policy can clear Core Identity but does not mark the player display as exact.
- Explicitly rejects broad missing-glyph cases such as `Drpeek -> Ieek` and `N E R D -> NER0`; those remain true OCR/reconstruction blockers.
- Preserves DataGuard: no Operational Truth mutation, no historical identity database, no manual mapping.

Validation: 21 focused smoke tests passed.

---

<!-- Consolidated from RELEASE_NOTES_PATCH10A.md -->

## v0.9.5.121

- Planning sprint for Evidence-first improvements.
- Added roadmap for Crop Geometry Inspector, Row Alignment Heatmap, Evidence Timeline and Fragment Voting Visualizer.
- No functional code changes in this documentation handover sprint.

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

<!-- Consolidated from RELEASE_NOTES_v0.9.5.30.md -->

## v0.9.5.121

- Planning sprint for Evidence-first improvements.
- Added roadmap for Crop Geometry Inspector, Row Alignment Heatmap, Evidence Timeline and Fragment Voting Visualizer.
- No functional code changes in this documentation handover sprint.

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

<!-- Consolidated from RELEASE_NOTES_v0.9.5.31.md -->

## v0.9.5.121

- Planning sprint for Evidence-first improvements.
- Added roadmap for Crop Geometry Inspector, Row Alignment Heatmap, Evidence Timeline and Fragment Voting Visualizer.
- No functional code changes in this documentation handover sprint.

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

<!-- Consolidated from RELEASE_NOTES_v0.9.5.32.md -->

## v0.9.5.121

- Planning sprint for Evidence-first improvements.
- Added roadmap for Crop Geometry Inspector, Row Alignment Heatmap, Evidence Timeline and Fragment Voting Visualizer.
- No functional code changes in this documentation handover sprint.

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

<!-- Consolidated from RELEASE_NOTES_v0.9.5.34.md -->

## v0.9.5.121

- Planning sprint for Evidence-first improvements.
- Added roadmap for Crop Geometry Inspector, Row Alignment Heatmap, Evidence Timeline and Fragment Voting Visualizer.
- No functional code changes in this documentation handover sprint.

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

<!-- Consolidated from RELEASE_NOTES_v0.9.5.35.md -->

## v0.9.5.121

- Planning sprint for Evidence-first improvements.
- Added roadmap for Crop Geometry Inspector, Row Alignment Heatmap, Evidence Timeline and Fragment Voting Visualizer.
- No functional code changes in this documentation handover sprint.

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

<!-- Consolidated from RELEASE_NOTES_v0.9.5.36.md -->

## v0.9.5.121

- Planning sprint for Evidence-first improvements.
- Added roadmap for Crop Geometry Inspector, Row Alignment Heatmap, Evidence Timeline and Fragment Voting Visualizer.
- No functional code changes in this documentation handover sprint.

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

<!-- Consolidated from RELEASE_NOTES_v0.9.5.37.md -->

## v0.9.5.121

- Planning sprint for Evidence-first improvements.
- Added roadmap for Crop Geometry Inspector, Row Alignment Heatmap, Evidence Timeline and Fragment Voting Visualizer.
- No functional code changes in this documentation handover sprint.

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

<!-- Consolidated from RELEASE_NOTES_v0.9.5.38.md -->

## v0.9.5.121

- Planning sprint for Evidence-first improvements.
- Added roadmap for Crop Geometry Inspector, Row Alignment Heatmap, Evidence Timeline and Fragment Voting Visualizer.
- No functional code changes in this documentation handover sprint.

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

<!-- Consolidated from RELEASE_NOTES_v0.9.5.39.md -->

## v0.9.5.121

- Planning sprint for Evidence-first improvements.
- Added roadmap for Crop Geometry Inspector, Row Alignment Heatmap, Evidence Timeline and Fragment Voting Visualizer.
- No functional code changes in this documentation handover sprint.

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

<!-- Consolidated from RELEASE_NOTES_v0.9.5.40.md -->

## v0.9.5.121

- Planning sprint for Evidence-first improvements.
- Added roadmap for Crop Geometry Inspector, Row Alignment Heatmap, Evidence Timeline and Fragment Voting Visualizer.
- No functional code changes in this documentation handover sprint.

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

<!-- Consolidated from RELEASE_NOTES_v0.9.5.41.md -->

## v0.9.5.121

- Planning sprint for Evidence-first improvements.
- Added roadmap for Crop Geometry Inspector, Row Alignment Heatmap, Evidence Timeline and Fragment Voting Visualizer.
- No functional code changes in this documentation handover sprint.

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

<!-- Consolidated from RELEASE_NOTES_v0.9.5.42.md -->

## v0.9.5.121

- Planning sprint for Evidence-first improvements.
- Added roadmap for Crop Geometry Inspector, Row Alignment Heatmap, Evidence Timeline and Fragment Voting Visualizer.
- No functional code changes in this documentation handover sprint.

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

<!-- Consolidated from RELEASE_NOTES_v0.9.5.43.md -->

## v0.9.5.121

- Planning sprint for Evidence-first improvements.
- Added roadmap for Crop Geometry Inspector, Row Alignment Heatmap, Evidence Timeline and Fragment Voting Visualizer.
- No functional code changes in this documentation handover sprint.

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

<!-- Consolidated from RELEASE_NOTES_v0.9.5.44.md -->

## v0.9.5.121

- Planning sprint for Evidence-first improvements.
- Added roadmap for Crop Geometry Inspector, Row Alignment Heatmap, Evidence Timeline and Fragment Voting Visualizer.
- No functional code changes in this documentation handover sprint.

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

<!-- Consolidated from RELEASE_NOTES_v0.9.5.45.md -->

## v0.9.5.121

- Planning sprint for Evidence-first improvements.
- Added roadmap for Crop Geometry Inspector, Row Alignment Heatmap, Evidence Timeline and Fragment Voting Visualizer.
- No functional code changes in this documentation handover sprint.

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
22 passed
```

## Commit

```bash
git add .
git commit -m "fix(ranking-guard): recover source-local leading digit power errors"
git tag -a v0.9.5.45 -m "v0.9.5.45 Source-local Power Digit Recovery"
```


---

<!-- Consolidated from docs_RELEASE_NOTES_v0.9.5.17.md -->

## v0.9.5.121

- Planning sprint for Evidence-first improvements.
- Added roadmap for Crop Geometry Inspector, Row Alignment Heatmap, Evidence Timeline and Fragment Voting Visualizer.
- No functional code changes in this documentation handover sprint.

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


## v0.9.5.131 – Display Reconstruction Engine Phase I

- Added a read-only Display Reconstruction Engine inside `ground_truth_validator.py`.
- New report outputs:
  - `display_reconstruction_report.json`
  - `display_reconstruction_report.xlsx`
  - `display_reconstruct` and `display_recon_rows` sheets in the main validation workbook.
- The engine consumes existing Character ReOCR evidence and read-only contextual inference evidence to produce report-only fields:
  - `display_reconstructed_name`
  - `display_reconstructed_alliance_tag`
  - `display_reconstruction_status`
  - `display_reconstruction_source`
  - `display_reconstruction_confidence`
  - `display_reconstruction_operational_truth_modified`
- Guardrail: no Ground Truth, OCR export, snapshot, verified display field, or Operational Truth field is modified.
- Added smoke tests for local character reconstruction, context-gap display suggestions, and report generation.

Strategic intent: Sentinel now starts converting stored character evidence into explainable display proposals without weakening DataGuard.

## v0.9.5.132 – Display Reconstruction Guard

- Added promotion control for Display Reconstruction Engine Phase I.
- Prevents unsafe display-name synthesis such as rebuilding names from `UNKNOWN` with sparse fragments.
- Adds `display_promotion_eligible` and `display_promotion_block_reason` to validation/detail reports.
- Introduces guarded statuses for blocked name promotion while preserving safe alliance reconstruction.
- Keeps Display Reconstruction strictly read-only: no Ground Truth, snapshot, export, or Operational Truth mutation.

## v0.9.5.133 – Evidence Confidence Engine

### Goal
Introduce a read-only Evidence Confidence layer for Display Reconstruction. The previous guard prevented unsafe promotion; this sprint explains *why* evidence is eligible, suggested, or blocked.

### Added
- `evidence_confidence_report.json/xlsx`.
- Fragment-level confidence scoring components:
  - crop quality
  - OCR confidence
  - vote consensus
  - position stability
  - unicode/script class
  - status weight
- Display coverage metrics:
  - `display_name_coverage_score`
  - `display_alliance_coverage_score`
  - `display_coverage_score`
- `display_confidence_decision` classification:
  - `eligible`
  - `suggested_evidence_only`
  - `suggested_contextual`
  - `blocked_low_evidence`
- Promotion Guard 2.0: Evidence Confidence can only tighten promotion decisions, never loosen DataGuard rules.

### Guardrails
- Operational Truth remains unchanged.
- Context-gap suggestions remain evidence-only.
- Low-confidence fragment sets are blocked from display promotion.
- No historical player memory is used as primary identity evidence.


## v0.9.5.134 – Evidence Budget Manager

This release adds a read-only Evidence Budget Manager for Display Fidelity. The new budget layer scores display reconstruction candidates before future expensive ReOCR work is promoted into the active pipeline. It introduces `evidence_priority_score`, `evidence_budget_tier`, `evidence_budget_action`, `evidence_budget_reason`, and the standalone `evidence_budget_report.json/xlsx`.

The sprint does not change Operational Truth, snapshots, exports, Ground Truth, or DataGuard policy. Its purpose is to make future Character ReOCR investment explainable and selective: high-value candidates can receive full budget, medium candidates receive targeted budget, weak evidence is blocked early or served from cache.


## v0.9.5.135 – Evidence Scheduler Phase I

- Added read-only Evidence Scheduler on top of the Evidence Budget Manager.
- Added `evidence_scheduler_report.json` and `evidence_scheduler_report.xlsx`.
- Introduced scheduler fields: `evidence_scheduler_decision`, `scheduler_priority`, `scheduler_reason`, `scheduler_expected_runtime_ms`, `scheduler_estimated_saved_ms`.
- Added queue decisions for full ReOCR, targeted ReOCR, limited retry, early exit/cache-only, and context-only evidence.
- Operational Truth remains locked; scheduler output is report-only in Phase I.

## v0.9.5.136 – Gold Accuracy Mode

Functional accuracy sprint. Sentinel now treats runtime as secondary during Gold Fidelity work. `GOLD_ACCURACY_MODE` is enabled in the validator, local glyph ReOCR budget skips are disabled, and Evidence Scheduler decisions no longer early-exit rows solely to save runtime. Context-gap evidence remains read-only and Operational Truth remains locked.

## v0.9.5.143 – Gold Core Strike IV

- Added read-only Gold Core root-cause analytics.
- Added persistent `gold_core_failure_memory.json`.
- Added `gold_core_analytics_report.json` and `.xlsx`.
- Added evidence-based recommendations per Gold Core case.
- Added regression coverage for Strike IV.
- Operational Truth remains unchanged.

## v0.9.5.144 – Gold Core Strike V: Knowledge Consolidation

- Established Gold Core triage is now the authoritative Root Cause Truth chain.
- Strike IV heuristics were demoted to fallback-only status and cannot overwrite
  `gold_core_failure_class`, `gold_core_failure_domain`, or `gold_core_fix_lane`.
- Added stable benchmark case IDs based on server and rank.
- Added `gold_core_case_explorer.json` and `gold_core_case_explorer.xlsx`.
- Added a generated `GOLD_CORE_CASEBOOK.md` per validator run.
- Added cross-report links for blocker, resolution, OCR evidence, character position,
  display reconstruction, analytics, and Failure Memory reports.
- Added recommendation scoring and expected-impact aggregation.
- Upgraded Failure Memory with solved/regression versions, owner, occurrence count,
  first/last seen, stable IDs, priority, and authoritative truth fields.
- Alliance-tag extraction remains separated from multilingual player-name analysis.
- Operational Truth remains unchanged.

## v0.9.5.145 — Gold Core Zero I

- Added a deterministic warning-only Vote Selection Policy gate.
- Clears a Gold Core blocker only when the selected screenshot-local glyph equals the expected glyph, no observed/unresolved/crop-conflict evidence exists, and name, alliance and power anchors independently agree.
- Added explicit vote-policy diagnostics to the Gold Core elimination report.
- Normalized Gold Case status to `OPEN` / `RESOLVED` and removed `nan` classification leakage.
- Added regression coverage for safe clearance and all principal stop signs.
- Operational Truth and OCR exports remain unchanged.


## v0.9.5.146 — Gold Core Zero II: Promotion Guard Rationalization

- Added complete promotion-guard diagnostics per Gold Core candidate.
- Added explicit failed-check lists, primary blocker, legacy reason, and evidence counters to the Gold Core elimination report.
- Added a narrow promotion-guard override only for authoritative `vote_warning_gate_review` cases blocked by low coverage or budget policy.
- Override requires accepted matching, exact name proof, alliance proof, power proof, expected-only current-screenshot vote consensus, and zero observed, unresolved, or crop-field counterevidence.
- Crop geometry, script policy, mixed blockers, context gaps, and observed-text conflicts remain hard blocked.
- Failure Memory records newly resolved cases as solved in v0.9.5.146.
- Operational Truth, Ground Truth, snapshots, and OCR exports remain unchanged.

## v0.9.5.147 — Gold Core Zero III: Evidence-Bound Name Reconstruction

- Added position-bound name proof states and complete reconstruction diagnostics.
- Added `clear_gold_core_blocker_evidence_reconstructed_name`.
- Equal source characters and verified screenshot-local ReOCR fragments are the only accepted position proofs.
- Missing positions remain explicit; Ground Truth is never used as an unobserved fill source.
- `UNKNOWN`, partial coverage, conflicting evidence, crop mismatch, alliance mismatch, and power mismatch remain blocked.
- Failure Memory records evidence-bound reconstruction metadata.
- Operational Truth remains unchanged.


## Archived content consolidated from `RELEASE_NOTED.md`

# RELEASE_NOTED.md

Canonical release notes live in `RELEASE_NOTES.md`. This file exists only as a compatibility pointer because the handover request mentioned `RELEASE_NOTED.md`.


## v0.9.5.130
- Strategic focus shifted from OCR accuracy to Display Reconstruction Engine.
- Documented next milestone around verified_display_name / verified_display_alliance_tag.
- Updated roadmap based on latest validation reports.


## v0.9.5.131 – Display Reconstruction Engine Phase I

- Added a read-only Display Reconstruction Engine inside `ground_truth_validator.py`.
- New report outputs:
  - `display_reconstruction_report.json`
  - `display_reconstruction_report.xlsx`
  - `display_reconstruct` and `display_recon_rows` sheets in the main validation workbook.
- The engine consumes existing Character ReOCR evidence and read-only contextual inference evidence to produce report-only fields:
  - `display_reconstructed_name`
  - `display_reconstructed_alliance_tag`
  - `display_reconstruction_status`
  - `display_reconstruction_source`
  - `display_reconstruction_confidence`
  - `display_reconstruction_operational_truth_modified`
- Guardrail: no Ground Truth, OCR export, snapshot, verified display field, or Operational Truth field is modified.
- Added smoke tests for local character reconstruction, context-gap display suggestions, and report generation.

Strategic intent: Sentinel now starts converting stored character evidence into explainable display proposals without weakening DataGuard.

## v0.9.5.132 – Display Reconstruction Guard

- Added guarded promotion rules for report-only display reconstruction.
- Blocks unsafe name promotion from `UNKNOWN`, low coverage, unresolved fragments, or observed-vote conflicts.
- Added `display_promotion_eligible` and `display_promotion_block_reason`.
- Operational Truth remains unchanged.

## v0.9.5.133 – Evidence Confidence Engine

- Added read-only `evidence_confidence_report.json/xlsx`.
- Added fragment confidence components for crop, OCR, votes, position, unicode/script and status.
- Added display coverage metrics for name/tag/display proposals.
- Added `display_confidence_decision`.
- DataGuard remains unchanged; Operational Truth is not modified.


## v0.9.5.134 – Evidence Budget Manager

- Added `evidence_budget_report.json` and `evidence_budget_report.xlsx`.
- Added read-only fields: `evidence_priority_score`, `evidence_budget_tier`, `evidence_budget_action`, `evidence_budget_reason`.
- Added budget recommendation layer for future Character ReOCR runtime reduction.
- Operational Truth remains unchanged.


## v0.9.5.135 – Evidence Scheduler Phase I

- Added read-only Evidence Scheduler reports and queue decisions.
- Converts passive Evidence Budget recommendations into an execution plan.
- No Operational Truth mutation.

## v0.9.5.136 – Gold Accuracy Mode

Functional accuracy sprint. Sentinel now treats runtime as secondary during Gold Fidelity work. `GOLD_ACCURACY_MODE` is enabled in the validator, local glyph ReOCR budget skips are disabled, and Evidence Scheduler decisions no longer early-exit rows solely to save runtime. Context-gap evidence remains read-only and Operational Truth remains locked.



## Archived content consolidated from `docs_RELEASE_NOTES_v0.9.5.17.md`

## v0.9.5.121

- Planning sprint for Evidence-first improvements.
- Added roadmap for Crop Geometry Inspector, Row Alignment Heatmap, Evidence Timeline and Fragment Voting Visualizer.
- No functional code changes in this documentation handover sprint.

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
