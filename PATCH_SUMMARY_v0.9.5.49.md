# Sentinel v0.9.5.49 – Candidate Decision Engine Cutover

## Focus

Out with the old: removes the legacy leading-digit power recovery fallback from the decision path.

In with the new: recovered power values are selected only by the context candidate decision engine when the best candidate has a clear score and margin.

## Changed

- Removed `legacy_leading_digit_recovery` as a recovery decision fallback.
- Keeps leading-digit variants only as generated candidates.
- Recovers only when candidate scoring produces a clear winner.
- Quarantines ambiguous candidate ties instead of silently recovering.
- Adds decision audit metadata:
  - `power_recovery_decision_strategy`,
  - `power_recovery_decision_version`,
  - `power_recovery_legacy_used`.

## Updated

- `parser/ranking_power_sanity_guard.py`
- `services/import_repository.py`
- `parser/excel.py`
- `tests/smoke/test_ranking_power_sanity_guard.py`
- `tests/smoke/test_operational_import_repository.py`
- `version.py`
- Sentinel documentation under `/docs`

## Validation

```text
python -m compileall -q parser services main.py version.py
pytest tests/smoke/test_ranking_power_sanity_guard.py tests/smoke/test_operational_import_repository.py tests/smoke/test_sentinel_ranking_guard.py tests/smoke/test_ranking_recovery.py -q
23 passed
```

## Commit

```bash
git add .
git commit -m "fix(recovery): remove legacy power recovery fallback"
git tag -a v0.9.5.49 -m "v0.9.5.49 Candidate Decision Engine Cutover"
```
