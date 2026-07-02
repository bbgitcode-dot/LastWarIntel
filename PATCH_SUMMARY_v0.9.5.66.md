<!-- Source: PATCH_SUMMARY_v0.9.5.66.md -->

# Sentinel v0.9.5.66 Patch Summary

## Version

v0.9.5.66 – Operational Readiness Drilldown

## Purpose

Adds a server-level Operational Readiness layer to the Command Center start page so the Proud Owner can immediately see how much of the server dataset is usable and where action is required.

## Changes

- Added Operational Readiness view models: status cards, server health items, and coverage summary.
- Added Command Center KPI cards for discovered servers, operational servers, pending reviews, missing data, and failed imports.
- Added drill-down links from KPI cards to Servers, Reviews, Quality, and Imports.
- Added a compact server health strip on the Command Center start page.
- Added drill-down banners to destination pages when filter links are used.
- Updated documentation and version to v0.9.5.66.

## Validation

```text
pytest tests/smoke/test_web_navigation_consolidation.py -q
10 passed
python -m compileall -q application/command_center web/app.py web/navigation.py web/routes web/templates services/command_center.py version.py
passed
```

Note: full `pytest tests/smoke -q` still encounters pre-existing legacy collection errors in unrelated smoke files with command-line snippets or older OCR config imports.

## Commit

```bash
git add .
git commit -m "feat(command): add operational readiness drilldown"
git tag -a v0.9.5.66 -m "v0.9.5.66 Operational Readiness Drilldown"
```
