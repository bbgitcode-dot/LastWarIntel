# Sentinel v0.9.5.39 – General Top Alliance Power Allowance

## Focus

Finalizes the Ranking Power Sanity Guard behavior for multi-server regression runs.

## Fixed

- Generalizes the top Alliance Power allowance introduced for Server 552 so it also protects legitimate top-of-source rows from desktop captures.
- Prevents real leading alliances such as strong Server 550/551 Alliance Power rows from being quarantined only because their screenshot-local median is much lower.
- Preserves quarantine behavior for late-row Alliance Power spikes and late-scroll THP OCR outliers.

## Validation

```text
pytest tests/smoke/test_ranking_power_sanity_guard.py -q
pytest tests/smoke -q
```

Expected operational validation:

```text
python main.py
python ground_truth_validator.py
```

## Commit

```bash
git add .
git commit -m "fix(ranking): generalize top alliance power allowance"
git tag -a v0.9.5.39 -m "v0.9.5.39 General Top Alliance Power Allowance"
```
