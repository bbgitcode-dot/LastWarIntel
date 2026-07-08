# Patch Summary

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
