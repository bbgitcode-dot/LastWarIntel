# Patch Summary – v0.9.5.94

## Sentinel v0.9.5.94 – Identity Fidelity Metrics & Risk Reporting

This sprint follows the Server 551 v0.9.5.93 validation. v0.9.5.93 fixed review leakage, but the Ground Truth report still showed that row matching can hide identity drift such as `Joncollins21` -> `Joncollinszl`. v0.9.5.94 makes exact identity preservation measurable.

## Changed

- Version bumped to `0.9.5.94`.
- Ground Truth validator now preserves case-sensitive display alliance tags before canonical matching.
- Added strict identity metrics: exact player display match, exact alliance display match, exact identity match, identity risk rows, high-value identity risk rows, case-sensitive tag mismatches, player-name drift rows and identity fidelity score.
- Added `identity_risk_summary` and `identity_risks` to JSON/XLSX reports.
- Added smoke tests for fuzzy player-name drift and case-sensitive alliance-tag drift.
- Updated docs to make Identity Fidelity a V1 gate.

## Validation

```text
pytest -q tests/smoke/test_identity_fidelity_validator.py
pytest -q tests/smoke/test_ground_truth_validator.py tests/smoke/test_validator_match_discipline.py tests/smoke/test_command_center.py tests/smoke/test_gap_resolver.py
python -m py_compile ground_truth_validator.py parser/identity_guard.py
zip -T Sentinel_v0.9.5.94.zip
```

## Commit

```bash
git add .
git commit -m "feat(data-guard): report exact identity fidelity risks"
git tag -a v0.9.5.94 -m "v0.9.5.94 Identity Fidelity Metrics and Risk Reporting"
```
