# Patch Summary – v0.9.5.89

## Sentinel v0.9.5.89 – Non-cache Data Quality Validation & Rank Slot Regression

This patch continues the data-quality stabilization line. It does not expand Intelligence. It protects rank-slot visibility and raw display fidelity across validation and export surfaces.

### Changed

- Bumped project version to `0.9.5.89`.
- Added v0.9.5.89 smoke regressions for cache-off validation defaults, rank-slot preservation, `Sven the vän` / `[SWSq]` raw display fidelity and export visibility.
- Excel exports now include pending-slot and observed/normalized/canonical identity fields for normal ranking sheets and quarantine/review sheets.
- Recognition-quality telemetry version now reports `v0.9.5.89` while unchanged power-recovery decisions still report their original decision version.
- Updated `/docs` with the v0.9.5.89 state, validation results and next-chat handoff.

### Validation

```text
pytest tests/smoke/test_data_quality_87.py tests/smoke/test_data_quality_89.py -q
7 passed

pytest tests/smoke/test_ranking_power_sanity_guard.py tests/smoke/test_data_quality_87.py tests/smoke/test_data_quality_89.py tests/smoke/test_recognition_quality_82.py -q
27 passed

python -m compileall -q main.py parser services application web version.py
OK

Full smoke collection attempted:
pytest tests/smoke -q
blocked during collection by pre-existing legacy invalid/stale tests:
- tests/smoke/test_calculator.py contains a shell command, not Python test code
- tests/smoke/test_orchestrator.py contains a shell command, not Python test code
- tests/smoke/test_easyocr_language_compatibility_hotfix.py imports removed/stale config symbol get_ocr_language_groups
- tests/smoke/test_multilingual_ocr_configuration.py imports removed/stale config symbol DEFAULT_OCR_LANGUAGES
```

### Git

```bash
git add .
git commit -m "test(data-quality): preserve rank slots and raw identity in exports"
git tag -a v0.9.5.89 -m "v0.9.5.89 Non-cache Data Quality Validation and Rank Slot Regression"
```
