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
