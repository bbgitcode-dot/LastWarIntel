# Sentinel v0.9.5.65 Patch Summary

## Version

v0.9.5.65 – Screenshot Highlight Calibration

## Purpose

Calibrates the Review Detail screenshot rank overlay so the marker aligns with the first visible ranking row instead of landing too low in the screenshot preview. Improves reviewer trust by treating the overlay as a visual aid with explicit approximate-state handling.

## Changes

- Replaced the naive v0.9.5.64 rank-to-y-position heuristic with ranking-type overlay profiles.
- Calibrated `alliance_power` and `total_hero_power` first-row anchors and row spacing against current Last War screenshot geometry.
- Added highlight metadata: label and approximate flag.
- Added human-friendly dotted number formatting for review choices in Review Detail.
- Kept screenshot links opening in a new tab.
- Added smoke coverage for calibrated first-row overlay positions.
- Updated documentation and version to v0.9.5.65.

## Validation

```text
pytest tests/smoke -q
compileall web/app.py web/navigation.py web/routes web/templates services/command_center.py version.py
```

## Commit

```bash
git add .
git commit -m "fix(review): calibrate screenshot rank highlight overlay"
git tag -a v0.9.5.65 -m "v0.9.5.65 Screenshot Highlight Calibration"
```
