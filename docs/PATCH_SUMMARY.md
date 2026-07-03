# Patch Summary – v0.9.5.78

## Title
Developer Benchmark & Report Rebuild Mode

## Baseline
Sentinel v0.9.5.77 – Review Context & Explainability

## Purpose
The 99-screenshot benchmark is too expensive to rerun for every review UI or report iteration. v0.9.5.78 adds safe developer run modes so Review Context, Evidence Pack and Command Center changes can be validated with targeted screenshots or by rebuilding reports from the latest import JSON.

## Included

- Added CLI argument parsing to `main.py`.
- Added `--rebuild-reports` for no-OCR static report regeneration.
- Added `--screenshots` filename/glob filter for small targeted OCR runs.
- Added `--limit` for quick smoke runs.
- Added `--skip-excel` and `--skip-command-center` for faster local profiling.
- Added `SENTINEL_SCREENSHOTS` and `SENTINEL_SCREENSHOT_LIMIT` environment fallbacks.
- Added smoke tests covering screenshot selection and rebuild parsing.
- Updated recognition telemetry version to `v0.9.5.78`.

## Commands

Fast report/UI validation after template/report changes:

```bash
python main.py --rebuild-reports
```

Targeted Review Context validation:

```bash
python main.py --screenshots "Screenshot_20260702-082210.png" --skip-excel
```

Small OCR benchmark:

```bash
python main.py --screenshots "*082210*.png,*194413*.png" --skip-command-center
```

## Validation

```text
python -m compileall -q main.py services web parser application
pytest -q tests/smoke/test_developer_run_modes.py tests/smoke/test_review_rank_trace.py tests/smoke/test_review_context.py tests/smoke/test_command_center.py tests/smoke/test_operational_import_repository.py
15 passed
zip integrity OK
```

## Git

```bash
git add .
git commit -m "chore(dev): add benchmark and report rebuild modes"
git tag -a v0.9.5.78 -m "v0.9.5.78 Developer Benchmark and Report Rebuild Mode"
```
