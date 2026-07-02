# Sentinel v0.9.5.60 Patch Summary

## Title
Command Center Consolidation & Review History Dedupe

## Purpose
v0.9.5.60 consolidates Sentinel's review/navigation structure and fixes persistent review history duplication. The sprint keeps OCR and recovery logic unchanged and focuses on the operator workflow around imports, quality, reviews, and evidence.

## Changes
- Added stable review identity keys independent of runtime timestamps.
- Review history now updates existing open reviews via `last_seen_at` and `seen_count` instead of creating duplicate open records on reruns.
- Existing duplicated v0.9.5.59 history is normalized and collapsed on the next Command Center generation.
- Added `/reviews` web route as the unified Review Center entry point.
- Added `web/templates/reviews.html` with open reviews, history, and static evidence links.
- Mounted `output/` as `/static-output` for current run-detail HTML during consolidation.
- Updated navigation language around Command Center, Imports, Quality, Reviews, and Operations.
- Static HTML labels now treat Evidence Pack as review detail/evidence rather than a competing Command Center.
- Updated version to `0.9.5.60`.

## Validation
- `pytest tests/smoke/test_command_center.py`
- `python -m compileall services/command_center.py web/app.py web/routes/reviews.py version.py`

## Commit
```bash
git add .
git commit -m "feat(ui): consolidate review center navigation"
git tag -a v0.9.5.60 -m "v0.9.5.60 Command Center Consolidation"
```
