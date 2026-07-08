# Patch Summary – v0.9.5.124 Gold Fidelity Engine Phase 1

## Purpose

This sprint starts the Gold Fidelity Engine by reusing screenshot-local evidence instead of repeatedly invoking CPU-heavy Character ReOCR for identical glyph claims inside one validation run. It preserves Data Guard: cached evidence is provenance-marked and never changes Operational Truth.

## Changes

- Added conservative snapshot-local ReOCR evidence cache.
- Added exact cache keys by target field, position, expected/observed glyph, reason, expected text, and observed text.
- Cached only decisive `verified_expected` / `verified_observed` outcomes.
- Cloned cache hits as `CharacterVerificationEvidence` with `reason=evidence_cache_hit`, `crop_strategy=snapshot_evidence_cache`, zero timing, and no crop box/votes.
- Added validator detail telemetry columns:
  - `reocr_evidence_cache_hits`
  - `reocr_evidence_cache_misses`
  - `reocr_evidence_cache_writes`
  - `reocr_evidence_cache_saved_reocr`
- Added focused smoke tests for cache behavior.

## Validation

```text
focused smoke tests passed
py_compile OK
zip integrity OK
```

## Commit

```bash
git add .
git commit -m "perf(gold-fidelity): cache reusable reocr evidence"
git tag -a v0.9.5.124 -m "v0.9.5.124 Gold Fidelity Engine Phase 1"
```
