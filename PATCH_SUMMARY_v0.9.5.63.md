# Sentinel v0.9.5.63 Patch Summary

## Sprint
Human Review Screenshot Evidence

## Changes
- Added `/screenshots` static route for source screenshot evidence.
- Review Detail now renders screenshot filename as an open-in-new-tab link.
- Review Detail now includes a screenshot preview panel that opens the original screenshot.
- Review Queue screenshot references are clickable.
- Added CSS for screenshot evidence panels matching the Command Center style.
- Added smoke tests for screenshot links, preview markup, safe URL generation, and static mount.
- Updated docs and version metadata.

## Validation
```text
pytest tests/smoke/test_web_navigation_consolidation.py tests/smoke/test_command_center.py
python -m compileall web/app.py web/navigation.py web/routes web/templates services/command_center.py version.py
```

## Commit
```bash
git add .
git commit -m "fix(review): link screenshot evidence from review detail"
git tag -a v0.9.5.63 -m "v0.9.5.63 Human Review Screenshot Evidence"
```
