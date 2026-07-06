# Sentinel v0.9.5.114 Patch Summary

## Focus
Player Name Drift Triage + Core Identity Gold Gate Cleanup.

## Key Changes
- Adds Core Identity metrics separate from strict full-row Gold Fidelity.
- Adds report sections/sheets for core identity matches and remaining core blockers.
- Reclassifies rank-only blockers so they no longer hide true player-name/tag problems.
- Keeps DataGuard conservative: no Operational Truth mutation, no new OCR correction path, no historical identity dependency.

## Validation
- Targeted smoke tests for v0.9.5.112 verified display, v0.9.5.113 triage, and v0.9.5.114 core gate passed.
- py_compile passed.
