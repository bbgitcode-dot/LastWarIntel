# Patch Summary – v0.9.5.123 Evidence Triage and ReOCR Stop Rules

## Purpose

This sprint turns the .122 performance findings into policy. The validator now distinguishes missing evidence from intentionally skipped evidence, and it stops spending CPU on low-yield ReOCR once Core Identity is already stable.

## Changes

- Added pre-ReOCR Core Safety Gate.
- Added low-yield player-target budget skip for already stable Core Identity cases.
- Preserved true glyph-repair paths such as `Joncollins21` by requiring stricter containment/high-confidence conditions before skipping player ReOCR.
- Added `not_requested_policy_nonlocal` for multilingual/nonlocal targets that Character ReOCR cannot safely solve.
- Added row integrity split:
  - `ROW_OK_POLICY_NONLOCAL`
  - `ROW_POLICY_NONLOCAL_REVIEW`
  - `ROW_POLICY_BUDGET_REVIEW`
- Added a soft ReOCR target timeout in `parser/targeted_character_reocr.py`.
- Full Gold remains strict; Core Truth and Full Fidelity remain separate.

## Validation

```text
53 focused smoke tests passed
py_compile OK
zip integrity OK
```

## Commit

```bash
git add .
git commit -m "perf(data-guard): triage evidence and stop low-yield reocr"
git tag -a v0.9.5.123 -m "v0.9.5.123 Evidence Triage and ReOCR Stop Rules"
```
