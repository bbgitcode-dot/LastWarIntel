# Patch Summary – v0.9.5.93

## Sentinel v0.9.5.93 – Review Export Separation & Identity Fidelity Guard

This sprint follows the Server 551 v0.9.5.92 validation. v0.9.5.92 restored clean rank output for accepted rows, but review placeholders leaked into normal THP output as artificial ranks 102-105. v0.9.5.93 removes these placeholders from normal Operational Truth exports and console summaries while preserving them in review/quarantine surfaces.

## Changes

- Version bumped to `0.9.5.93`.
- Normal ranking summaries and Excel sheets filter synthetic `PENDING REVIEW` rows.
- Review/quarantine rows remain available in `REVIEW_ranking_guard_quarantine`, Review Dashboard and Evidence Pack.
- Source evidence and screenshot rank-window inference ignore pending placeholders so review windows are not stretched by artificial ranks.
- Added `parser/identity_guard.py` with first Identity Fidelity risk metadata.
- Added identity fields to THP rows: `identity_fidelity_status`, `identity_fidelity_risk`, `identity_fidelity_warnings`, `case_sensitive_alliance_tag`, `canonical_alliance_tag`.
- Documented that alliance tags are case-sensitive and player names such as `Joncollins21` must not be reduced to fuzzy OCR matches.

## Validation

```text
pytest tests/smoke/test_data_quality_89.py tests/smoke/test_data_quality_90.py tests/smoke/test_data_quality_91.py tests/smoke/test_data_quality_92.py tests/smoke/test_data_quality_93.py tests/smoke/test_ground_truth_validator.py -q
20 passed
python -m py_compile main.py parser/excel.py parser/identity_guard.py parser/player_ranking.py models/player_ranking.py services/import_repository.py version.py
zip -T Sentinel_v0.9.5.93.zip
```

Full smoke collection still contains pre-existing invalid/legacy tests unrelated to this sprint (`test_calculator.py`, `test_orchestrator.py`, and missing OCR config symbols).

## Commit

```bash
git add .
git commit -m "fix(data-guard): separate review placeholders from operational export"
git tag -a v0.9.5.93 -m "v0.9.5.93 Review Export Separation and Identity Fidelity Guard"
```
