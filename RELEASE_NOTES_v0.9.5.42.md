# Sentinel v0.9.5.42 – Ranking Segment Integrity Guard

## Focus

Protect ranking reconstruction from scroll-segment contamination without relying on screenshot filename order.

## Added

- Intrinsic THP rank/power envelope guard.
- Late-scroll THP rows with high OCR ranks and impossible top-whale powers are quarantined before final power sorting.
- Alliance Power rank/power envelope guard for non-top rows with impossible 50B+ values.
- Explainable quarantine reasons:
  - `thp_rank_power_envelope_violation`
  - `alliance_rank_power_envelope_violation`

## Why

Server 553 showed a new failure mode: late-scroll THP screenshots containing ranks around 100 were parsed with OCR digit explosions around 764M and then sorted above the real Rank 1 player. Earlier guards relied too much on source order, which is unsafe when future Discord or multi-user uploads can mix screenshots from different rankings.

This patch uses row-intrinsic evidence instead: OCR rank plus parsed power. A row that claims to be Rank 100 but carries a top-whale power value is not trusted. It is quarantined, not repaired.

## Expected impact

- Server 553 false THP leaders such as late-rank 764M rows should move to `REVIEW - ranking_guard_quarantine`.
- Server 553 Alliance Power false 77B non-top row should be quarantined.
- Existing 549–552 protections remain intact because the guard is intrinsic and conservative.

## Validation

```text
python -m compileall -q parser main.py ground_truth_validator.py
python main.py
python ground_truth_validator.py
```

## Commit

```bash
git add .
git commit -m "fix(ranking-guard): add intrinsic segment integrity guard"
git tag -a v0.9.5.42 -m "v0.9.5.42 Ranking Segment Integrity Guard"
git push origin main
git push origin v0.9.5.42
```
