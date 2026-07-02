# Sentinel v0.9.5.50 – Bidirectional Power Error Model

## Focus

Adds an OCR power error model to the candidate decision engine introduced in v0.9.5.49.

v0.9.5.49 made high power explosion handling safe by removing legacy fallback decisions. v0.9.5.50 extends the same margin-gated recovery model to low/truncated THP values observed in the Server 549–553 regression run.

## Added

- Low/truncated THP candidate generation:
  - `scale_x10_truncated_digit`,
  - `scale_x100_truncated_digit`,
  - `insert_zero`.
- OCR error model scoring for high THP leading-digit explosions:
  - `leading_digit_to_1`,
  - `leading_digit_to_2`,
  - `leading_digit_to_3`.
- Regression tests for:
  - high THP explosion recovery,
  - low THP truncation recovery,
  - Alliance Power low-tail protection.

## Guardrails

- Recovery remains source-local.
- Recovery remains margin-gated.
- Ambiguous candidates still quarantine.
- Runtime does not use Ground Truth.
- Alliance Power low tails are not treated as THP truncation errors.

## Validation

```text
python -m compileall -q parser main.py ground_truth_validator.py sentinel.py version.py
pytest tests/smoke/test_ranking_power_sanity_guard.py tests/smoke/test_thp_power_sanity_guard.py tests/smoke/test_sentinel_ranking_guard.py tests/smoke/test_ranking_recovery.py tests/smoke/test_operational_import_repository.py -q
30 passed
```

## Commit

```bash
git add .
git commit -m "feat(recovery): add bidirectional OCR power error model"
git tag -a v0.9.5.50 -m "v0.9.5.50 Bidirectional Power Error Model"
```
