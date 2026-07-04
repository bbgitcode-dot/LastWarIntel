# Patch Summary – v0.9.5.90

## Sentinel v0.9.5.90 – Operational Truth Hardening

This sprint converts the .89 benchmark findings into Data Guard invariants. The core fix is that visible rank slots and raw OCR identity are now protected operational fields. Recovery may suggest or repair power only when safe; it must not move a row to another rank slot or overwrite the observed display identity.

## Implemented

- Version bumped to `0.9.5.90`.
- `merge_rows_by_power` now preserves explicit visible rank slots instead of rewriting them from power order.
- Added raw identity lock fields: `raw_player_name`, `raw_alliance_tag`, `raw_alliance_name`.
- Ambiguous high-explosion review placeholders no longer expose the false high OCR value as Operational Truth power.
- Ambiguous low-truncation placeholders keep observed power and raw identity while surfacing candidates as review evidence.
- Excel export surfaces `operational_rank`, `visible_rank` and raw identity columns.
- Added regression coverage for Server 553 `[SWSq] sven the vän`, candidate-only low-truncation review, and quarantine slot preservation.

## Validation

```text
python -m pytest tests/smoke/test_data_quality_90.py tests/smoke/test_data_quality_89.py tests/smoke/test_power_first_reconstruction.py tests/smoke/test_ranking_integrity_validation.py -q
10 passed

python -m pytest tests/smoke/test_ranking_power_sanity_guard.py tests/smoke/test_thp_power_sanity_guard.py tests/smoke/test_review_rank_trace.py tests/smoke/test_review_identity_consistency.py tests/smoke/test_data_quality_90.py -q
29 passed

python -m py_compile parser/ranking.py parser/ranking_power_sanity_guard.py parser/ranking_guard.py parser/excel.py version.py
OK

Full compileall note: baseline still contains pre-existing invalid RTF/stub Python files such as analysis/alliance.py

zip -T Sentinel_v0.9.5.90.zip
OK
```

## Commit

```bash
git add .
git commit -m "fix(data-guard): lock visible rank slots and raw identity"
git tag -a v0.9.5.90 -m "v0.9.5.90 Operational Truth Hardening"
```
