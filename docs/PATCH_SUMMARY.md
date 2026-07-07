# Patch Summary – v0.9.5.120 Latin Residual Validator Crashfix

## Purpose

v0.9.5.120 is a narrow hotfix for v0.9.5.119. The Latin Residual Core Gate referenced `expected_name_key` and `actual_name_key` before those variables were initialized in `validate()`, causing `ground_truth_validator.py` to crash before report generation.

## Changes

- Initialize `expected_name_key` and `actual_name_key` immediately after `normalize_player_name(...)` results are created.
- Keep the v0.9.5.119 Latin Residual Core policy unchanged.
- No new OCR behavior, no new DataGuard policy, no Operational Truth changes.

## Validation

- `python -m py_compile ground_truth_validator.py version.py`
- ZIP integrity check

