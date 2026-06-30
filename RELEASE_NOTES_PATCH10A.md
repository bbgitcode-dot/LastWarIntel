# Sentinel v0.9.5.29 – Ranking Guard Recovery

## Focus

Introduces a conservative Ranking Guard Recovery layer after the Ranking Guard and before quarantine.

The goal is not to guess corrected rankings. The goal is to recover only rows whose ranking-type assignment is provably safe, and to calibrate false-positive alliance-name shapes that previously filled quarantine.

## Added

- `parser/ranking_recovery.py`
  - Evidence-based recovery decisions for Ranking Guard quarantines.
  - Explicit distinction between `recovered`, `calibrated_pass`, and `quarantine`.
  - Safe THP recovery only when explicit player fields and player-scale power are present.
  - Alliance Power calibration for rows where bracketed alliance names mimic player tags but no explicit player fields exist.
- Ranking recovery metrics in `data/latest_import_report.json`:
  - attempts,
  - success,
  - calibrated_pass,
  - rejected,
  - confidence_avg.
- Smoke tests for Ranking Guard Recovery.

## Changed

- `parser/ranking_guard.py` now gives the recovery layer one conservative chance before quarantine.
- Ranking Guard remains the integrity gate; Recovery cannot bypass it.
- Rows recovered or calibrated by the recovery layer are annotated with explainable evidence fields.
- Version updated to `0.9.5.29`.

## Guardrail

Recovery is evidence-based only.

A row is not moved because it is convenient. It is moved only if row-level evidence proves a safer destination. If evidence is insufficient, quarantine remains the correct outcome.

## Validation

```text
python -m pytest tests/smoke/test_ranking_recovery.py tests/smoke/test_sentinel_ranking_guard.py tests/smoke/test_operational_import_repository.py -q
```

## Commit

```bash
git add .
git commit -m "feat(ranking): add evidence-based ranking guard recovery"
git tag -a v0.9.5.29 -m "v0.9.5.29 Ranking Guard Recovery"
```
