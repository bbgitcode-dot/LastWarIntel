# Patch Summary – v0.9.5.79

## Review Identity Consistency Fix

This patch fixes the confusing Review UX observed after v0.9.5.78: Review cards could still imply that a source-row ordinal was a true visible/global ranking rank, and new runs could restart the `REV-xxx` display counter.

## Changes

- Added conservative source-row handling for screenshots whose inferred rank window is only `1..N`.
- UI now renders `Source Row X · Visible Rank unresolved` when the global rank cannot be proven from the screenshot evidence.
- Evidence overlay labels row-only targets as `Row X` instead of `Rank X`.
- Review IDs are now assigned from persistent Review History:
  - existing business identities retain their old REV id,
  - new identities receive the next available REV number.
- Review identity includes the stable business context, not the current run ordinal.
- Added regression tests for source-row-only rank handling and monotonic Review IDs.

## Validation

```text
python -m compileall -q services web/routes
pytest -q tests/smoke/test_command_center.py tests/smoke/test_snapshot*.py tests/smoke/test_review*.py
19 passed
```

## Git

```bash
git add .
git commit -m "fix(review): keep review identity and source row consistent"
git tag -a v0.9.5.79 -m "v0.9.5.79 Review Identity Consistency Fix"
```
