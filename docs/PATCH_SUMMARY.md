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
