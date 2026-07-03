# Patch Summary – v0.9.5.80

## Sentinel v0.9.5.80 – Continuous Collection & Source-Row Review Clarity

This patch corrects two workflow issues found during the 99-screenshot recognition pass.

## Changes

- Normal screenshot import runs keep the active snapshot in `COLLECTING` so 24/7 screenshot intake is not blocked after every batch.
- `--finish-collection` is now the explicit operator action that advances a snapshot to `REVIEWING` or `VERIFIED`.
- Review UI and Evidence Pack no longer treat source-row-only evidence as a proven global visible rank.
- Source-row-only reviews display `Source Row N · Visible Rank unresolved` and highlight the row without claiming `Rank N`.

## Validation

```text
python -m pytest -q tests/smoke/test_review_identity_consistency.py
3 passed

python -m compileall -q main.py services/command_center.py web/routes/reviews.py services/import_repository.py application/snapshots/service.py
compileall OK
```

## Commit

```bash
git add .
git commit -m "fix(snapshot): keep collecting after imports"
git tag -a v0.9.5.80 -m "v0.9.5.80 Continuous Collection and Source-Row Review Clarity"
```
