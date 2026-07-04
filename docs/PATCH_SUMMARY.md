# Patch Summary – v0.9.5.92

## Sentinel v0.9.5.92 – Rank Inference & Export Precision Hardening

This sprint follows the isolated Server 551 validation run. v0.9.5.91 protected Ground Truth recall but over-quarantined rank context at the export boundary: many correct rows had `rank=None`. v0.9.5.92 adds context-aware rank inference for full-scope/multi-window imports while preserving screenshot-visible OCR evidence for audit.

## Changes

- Version bumped to `0.9.5.92`.
- Added full-scope rank inference in `parser/ranking.py`.
- Missing OCR rank in full-scope imports is inferred from power order.
- Clearly broken OCR ranks such as `800`, `300`, or similar rank-column artifacts are repaired to power-order rank while kept in `visible_rank`/`ocr_rank`.
- Partial forensic windows still preserve visible ranks such as 79/81 and do not collapse them to 1/2.
- Added v0.9.5.92 regression tests for:
  - missing visible ranks inferred from power order in full-scope imports;
  - bad OCR rank repaired while preserved as evidence;
  - partial-window visible ranks remaining authoritative.

## Validation

```text
pytest tests/smoke/test_data_quality_89.py tests/smoke/test_data_quality_90.py tests/smoke/test_data_quality_91.py tests/smoke/test_data_quality_92.py -q
pytest tests/smoke/test_power_first_reconstruction.py tests/smoke/test_ranking_integrity_validation.py -q
python -m py_compile parser/ranking.py version.py
zip -T Sentinel_v0.9.5.92.zip
```

## Commit

```bash
git add .
git commit -m "fix(data-guard): infer full-scope ranks without losing raw evidence"
git tag -a v0.9.5.92 -m "v0.9.5.92 Rank Inference and Export Precision Hardening"
```
