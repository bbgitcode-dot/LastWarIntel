# Sentinel v0.9.5.28 – Inference Engine Core

## Focus

Introduces the first read-only Inference Layer for Sentinel. The new Context Engine operates above Operational Truth and produces explicit, explainable validation inferences without modifying OCR output, parser rows, exports, or guard decisions.

## Added

- `inference/` package.
- `inference.context_engine.apply_contextual_inference()`.
- Contextual inference for single-row bounded ranking gaps.
- Inference metadata in Ground Truth validation details:
  - `inference_status`
  - `inference_confidence`
  - `inference_evidence`
  - `inference_decision`
- `benchmarks/inference_report.json`.
- `benchmarks/inference_report.xlsx`.
- Smoke tests for the Context Engine.

## Changed

- Ground Truth Validator can now distinguish observed matches from read-only contextual inferences.
- Recoverable bounded gaps can be resolved as `inference_context_gap` when trusted neighbor anchors and power continuity provide sufficient evidence.
- Validation summary now reports `inference_rows` and `inference_accepted_rows`.
- Version updated to `0.9.5.28`.

## Guardrail

Inference does not change Operational Truth. It does not alter the Sentinel export and does not override Data Guard or Ranking Guard decisions. It only records derived, explainable conclusions in validation/inference reports.

## Validation

```text
python -m compileall -q .
pytest tests/smoke/test_inference_context_engine.py tests/smoke/test_evidence_resolver.py tests/smoke/test_gap_recovery.py tests/smoke/test_ground_truth_validator.py tests/smoke/test_sentinel_data_guard.py tests/smoke/test_sentinel_ranking_guard.py -q
```

## Commit

```bash
git add .
git commit -m "feat(inference): introduce read-only context engine for v0.9.5.28"
git tag -a v0.9.5.28 -m "v0.9.5.28 Inference Engine Core"
```
