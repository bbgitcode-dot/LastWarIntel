# Sentinel v0.9.5.51 Patch Summary – Digit-Preserving Power Recovery

## Focus

Hardens the v0.9.5.50 bidirectional OCR power error model with explicit digit-preservation scoring for low/truncated THP recovery candidates.

## Why

The Server 549–553 regression run showed that v0.9.5.50 recovered many low-truncated THP rows, but some candidate choices were still too numerical-context-driven. A candidate can fit the local power envelope while distorting the visible OCR digit sequence.

## Changed

- Added `digit_preservation_score` to `PowerRecoveryCandidate`.
- Added candidate metadata export via `power_recovery_candidates`.
- Added candidate reason traces such as `digit_preservation:0.840`.
- Added a digit-preserving low-truncation decision path for narrow but strong candidate margins.
- Kept high explosion and Alliance Power decisions margin-gated.
- Updated recovery decision version to `v0.9.5.51`.
- Updated project docs, changelog, release notes, and version.

## Guardrail

Digit preservation is only a scoring signal. It does not bypass Data Guard, Ranking Guard, source-local context, or quarantine-first doctrine. Runtime still does not use Ground Truth, filename order, or upload order as truth.

## Validation

```text
python -m compileall -q parser services main.py ground_truth_validator.py sentinel.py version.py
pytest tests/smoke/test_ranking_power_sanity_guard.py tests/smoke/test_thp_power_sanity_guard.py tests/smoke/test_sentinel_ranking_guard.py tests/smoke/test_ranking_recovery.py tests/smoke/test_operational_import_repository.py -q
30 passed
```

Full `pytest tests/smoke -q` still collects pre-existing invalid/hotfix smoke files unrelated to this sprint.

## Commit

```bash
git add .
git commit -m "feat(recovery): add digit-preserving power candidate scoring"
git tag -a v0.9.5.51 -m "v0.9.5.51 Digit-Preserving Power Recovery"
```
