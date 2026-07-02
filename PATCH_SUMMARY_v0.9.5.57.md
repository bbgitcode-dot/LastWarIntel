# Sentinel v0.9.5.57 Patch Summary

## Sprint
Evidence Trace Binding

## Baseline
Sentinel_v0.9.56.zip

## Changes
- Bound Review Evidence Pack items to matching `power_recovery.traces` using exact matching and conservative screenshot-local fallback.
- Added fallback support for synthetic `ranking_guard_quarantine` traces when review rows expose expected ranking types.
- Added trace status, source file, candidate count, candidate reasons, and digit-preservation score to evidence cards.
- Added direct review-table links from Command Center / Review Dashboard to evidence-card anchors.
- Updated version to 0.9.5.57.
- Updated docs in `/docs`, including CHANGELOG, RELEASE_NOTES, PROJECT_STATUS, ROADMAP, and LESSONS_LEARNED.

## Validation
```text
pytest tests/smoke/test_command_center.py -q
2 passed
python -m compileall -q services/command_center.py main.py version.py
```

## Guardrail
Evidence Trace Binding is read-only. It improves explainability only and does not promote rows, resolve reviews, or alter Operational Truth.
