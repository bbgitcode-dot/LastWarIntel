# Sentinel v0.9.5.31 – Mobile Ranking Type Integrity Hotfix

## Focus

Fixes a blind-test issue found on Server 552 mobile German screenshots where lower Alliance Power pages were inferred as Total Hero Power after their values dropped below 1B.

## Fixed

- Detects German mobile ranking headers:
  - `Allianz-Kampfkraft` → `alliance_power`
  - `Gesamtkampfkraft der Helden` → `total_hero_power`
- Prevents low-rank Alliance Power rows from leaking into THP merely because their values are player-scale.
- Keeps genuine low-rank Alliance Power rows in Alliance Power when the source screen is classified as Alliance Power and the row has alliance-name-only shape.
- Keeps top-rank THP-shaped rows in Alliance Power quarantined instead of blindly accepting them.

## Guardrail

This patch does **not** weaken the Data Guard doctrine. It does not guess a ranking type from filenames or timestamps. It uses intrinsic screen/header evidence and conservative row-shape calibration.

## Validation

```text
10 passed
```

Targeted tests:

```bash
pytest tests/smoke/test_mobile_german_ranking_type_detection.py \
       tests/smoke/test_ranking_recovery.py \
       tests/smoke/test_sentinel_ranking_guard.py \
       tests/smoke/test_ranking_type_fallback.py -q
```

## Commit

```bash
git add .
git commit -m "fix(import): preserve mobile alliance ranking type integrity"
git tag -a v0.9.5.31 -m "v0.9.5.31 Mobile Ranking Type Integrity Hotfix"
```
