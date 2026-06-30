# Architecture Consolidation v0.9.5.20

## Purpose

Commit 4 separates operational runtime data from development validation artifacts.

## Rule

```text
Ground Truth validates Sentinel.
Repositories power Sentinel.
```

## Runtime Flow

```text
Command Center
  -> DataQualityService
  -> QualityReportRepository
  -> Operational report source
```

## Current Adapter

`services/quality_repository.py` contains the compatibility adapter for the latest validator JSON report.

This keeps the current workflow operational while preventing UI routes and application services from reading benchmark files directly.

## Future Replacement

The adapter can be replaced by SQLite/PostgreSQL without changing:

- `web/routes/*`
- `application/command_center/*`
- `web/templates/*`

## Existing Services Observation

The existing top-level `services/` package remains the integration point for persistence and operational access. No parallel service hierarchy was introduced.
