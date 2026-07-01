# Sentinel Release Notes

**Current Version:** v0.9.5.48

This file consolidates Sentinel release notes. Individual historical release-note files may remain in the repository for traceability, but this is the primary release history.

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
