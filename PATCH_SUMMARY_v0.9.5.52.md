# Sentinel v0.9.5.52 Patch Summary – Segment Order Recovery Guardrails

## Focus

v0.9.5.52 moves recovery hardening from raw power scoring into segment integrity. It keeps the bidirectional/digit-preserving candidate engine, adds a conservative segment-order tie-break for close high-explosion THP candidates, and quarantines low-truncation ties that remain ambiguous.

## Changed

- Added segment-order tie-break helper functions.
- High 7xxM THP candidates may recover an order-consistent near-tie candidate.
- Low/truncated THP recovery now requires stronger margin/digit evidence across multi-candidate cases.
- Updated recovery decision version to `v0.9.5.52`.
- Updated `/docs` release notes, changelog, architecture, project status, data guard notes, and lessons learned.

## Validation

```text
pytest tests/smoke/test_ranking_power_sanity_guard.py tests/smoke/test_operational_import_repository.py tests/smoke/test_ground_truth_validator.py tests/smoke/test_inference_context_engine.py tests/smoke/test_sentinel_data_guard.py -q
31 passed
```

## Commit

```bash
git add .
git commit -m "fix(recovery): add segment-order guardrails for power candidates"
git tag -a v0.9.5.52 -m "v0.9.5.52 Segment Order Recovery Guardrails"
```
