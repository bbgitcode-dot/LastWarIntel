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
