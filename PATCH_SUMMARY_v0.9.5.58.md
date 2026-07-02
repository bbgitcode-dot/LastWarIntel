# Sentinel v0.9.5.58 Patch Summary

## Theme
Human Review Guidance and Review History Foundation.

## Changes
- Added human-facing problem statements to Review Evidence Pack items.
- Added candidate choice lists: Vorschlag 1/2/3 plus manual input.
- Added problem type/label and confidence label metadata to evidence JSON.
- Added persistent `data/review_history.json` and mirrored `output/review_history.json`.
- Updated docs and version to 0.9.5.58.

## Validation
- `pytest tests/smoke/test_command_center.py -q`
- `python -m compileall services/command_center.py main.py version.py`
