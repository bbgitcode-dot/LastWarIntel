# Patch Summary – v0.9.5.86

**Theme:** Source Row Identity & Display Fidelity

This patch fixes the class of review errors where Sentinel described the right-looking candidate but highlighted or labelled the wrong screenshot row. The motivating case was Server 553 THP: `[SWSq] Sven the vän` was visually Rank 10, while the review rendered `[SWSQ] Sven the Van` at Rank 12.

## Changed

- `services/import_repository.py` now builds a same-screenshot source-evidence index from trusted non-quarantine rows.
- Ranking Guard quarantine reviews can be anchored to the observed screenshot row when name/alliance/power evidence matches strongly enough.
- Review target context prefers raw/observed identity fields before normalized fields.
- Recognition quality telemetry now reports `source_evidence_anchor_reviews`.
- Added smoke coverage for source-evidence anchoring and raw display preservation.

## Safety

The anchor uses only rows already observed on the same screenshot. It does not use filename order, upload order or screenshot order as truth. If no strong same-screenshot match exists, Sentinel keeps the conservative source-row / unresolved-rank behavior.

# Patch Summary – v0.9.5.85

**Theme:** Recovery Promotion Rules & OCR Cache

This patch turns the v0.9.5.84 diagnostics into two practical improvements: cached OCR observations for repeat/benchmark runs and a guarded promotion rule for one class of near-miss low-truncation power recoveries.

## Changed

- `parser/ocr_cache.py` introduces a persistent OCR cache under `data/ocr_cache/`.
- `main.py` now uses cached metadata/row OCR by default and exposes `--no-ocr-cache`.
- Runtime telemetry now includes `ocr_cache_hits`, `ocr_cache_misses`, `ocr_cache_writes`, and `ocr_cache_errors`.
- `parser/ranking_power_sanity_guard.py` adds a conservative near-miss low-truncation recovery path.
- `services/import_repository.py` reports recognition quality as `v0.9.5.85`.
- New smoke tests cover cache behavior and the promoted near-miss recovery class.

## Safety

The OCR cache is an observation cache only. It does not create Operational Truth, change Data Guard decisions, or infer server/rank from filename, upload order or screenshot order. Cache misses and cache errors fall back to live OCR.

# Patch Summary – v0.9.5.84

## Sentinel v0.9.5.84 – Power Recovery Diagnostics & Candidate Family Telemetry

This patch prepares the next recognition-tuning step by making power-recovery failures measurable by class. It does not relax Data Guard or Ranking Guard. Quarantine remains preferred over false Operational Truth.

### Changed

- Added `power_recovery_family` on recovered and ambiguous power-recovery rows.
- Added import-report counters:
  - `power_recovery.by_family`
  - `power_recovery.ambiguous_by_family`
  - `power_recovery.near_miss_ambiguous`
  - `recognition_quality.power_recovery_by_family`
  - `recognition_quality.ambiguous_power_by_family`
  - `recognition_quality.ambiguous_power_near_misses`
- Added recovery family labels to static Command Center trace tables.
- Added near-miss counts to Power Recovered metric cards.
- Bumped recognition quality telemetry version to `v0.9.5.84`.

### Validation

```text
19 passed (ranking power sanity + recognition quality smoke)
python -m compileall -q main.py parser services application web version.py
zip integrity OK
```

### Git

```bash
git add .
git commit -m "feat(recognition): classify power recovery families"
git tag -a v0.9.5.84 -m "v0.9.5.84 Power Recovery Diagnostics"
```

---

# Patch Summary – v0.9.5.82

## Sentinel v0.9.5.82 – Recognition Quality Pass

This patch turns the 99-screenshot production batch into measurable recognition quality telemetry. It does not expand Intelligence. It improves the ability to see where OCR/recovery time and review load are produced.

### Changed

- Added per-stage runtime telemetry to `main.py`.
- Extended import reports to schema `sentinel.import_run.v5`.
- Added recognition quality counters and recovery success rate.
- Added conservative high-explosion candidate auto-promotion for strong, order-consistent alliance-power candidates.
- Added Command Center cards for Recognition Quality and Runtime / Screenshot.
- Documentation updated for the recognition-quality sprint.

### Validation

```text
16 passed
compileall OK
zip integrity OK
```

### Git

```bash
git add .
git commit -m "feat(data-guard): add recognition quality telemetry"
git tag -a v0.9.5.82 -m "v0.9.5.82 Recognition Quality Pass"
```


---

# Patch Summary – v0.9.5.83

## Sentinel v0.9.5.83 – Rebuild Report Telemetry Hotfix

This patch fixes the fast report-rebuild loop introduced for recognition-quality work. `--rebuild-reports` now initializes runtime telemetry before any branch-specific code executes and can rebuild the Command Center, Review Dashboard and Evidence Pack without running OCR.

### Changed

- Moved `start_time` and `runtime_timings` initialization to the top of `main()`.
- Rebuild mode now records `html_report_render` and `total_runtime`.
- Rebuild mode prints runtime telemetry just like normal imports.
- Added a smoke test that exercises `main(["--rebuild-reports"])` with a mocked report renderer.

### Validation

```text
pytest tests/smoke/test_developer_run_modes.py -q
python -m compileall -q main.py services parser application version.py
zip integrity OK
```

### Git

```bash
git add .
git commit -m "fix(dev): initialize rebuild report telemetry"
git tag -a v0.9.5.83 -m "v0.9.5.83 Rebuild Report Telemetry Hotfix"
```
