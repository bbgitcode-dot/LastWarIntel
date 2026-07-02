# Sentinel v0.9.5.64 Patch Summary

## Release

v0.9.5.64 – Review Evidence Highlight Overlay

## Focus

Makes screenshot evidence usable inside Review Detail by reducing the preview footprint, switching to a two-column reviewer workspace, and highlighting the target rank directly on the screenshot preview. Also consolidates historical patch summaries into `/docs/PATCH_SUMMARY.md`.

## Key changes

- Added rank highlight overlay metadata for review detail items.
- Added compact screenshot evidence column with sticky preview.
- Added target-rank overlay and badge on screenshot previews.
- Kept full-resolution screenshot links opening in a new tab.
- Reworked Review Detail into a left decision column and right evidence column.
- Added `/docs/PATCH_SUMMARY.md` as the consolidated patch-summary register.
- Updated documentation and version to v0.9.5.64.

## Validation

```text
pytest tests/smoke/test_web_navigation_consolidation.py -q
9 passed
python -m compileall -q web/app.py web/navigation.py web/routes web/templates services/command_center.py version.py
passed
```

## Commit

```bash
git add .
git commit -m "feat(review): highlight target rank in screenshot evidence"
git tag -a v0.9.5.64 -m "v0.9.5.64 Review Evidence Highlight Overlay"
```
