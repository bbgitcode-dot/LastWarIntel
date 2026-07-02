# Sentinel Architecture

**Current version:** v0.9.5.72

Sentinel is an explainable strategic intelligence platform for Last War. Its current architecture is built around guarded data ingestion before strategic intelligence.

## High-level flow

```text
Screenshot / Excel / Manual Source
        ↓
Import Context / Snapshot
        ↓
OCR or Structured Import
        ↓
Parsing and Normalization
        ↓
Data Guard + Ranking Guard
        ↓
Recovery or Quarantine
        ↓
Human Review
        ↓
Operational Truth / Export / Historical Reference
        ↓
Command Center / Intelligence Layer
```

## Runtime components

- `main.py` – screenshot import orchestration.
- `parser/*` – OCR parsing, normalization, guards and recovery.
- `importer/historical_excel_import.py` – historical Excel import.
- `database/*` – SQLite schema and repositories.
- `application/command_center/*` – Command Center view model services.
- `application/historical_import/*` – historical import/report view services.
- `application/snapshots/*` – managed snapshot foundation.
- `web/routes/*` and `web/templates/*` – web UI for Command Center, Imports, Quality, Reviews and related pages.
- `docs/*` – project knowledge base.

## Source contexts

### Current Run
Latest screenshot OCR/import output. It is evidence, not automatically truth.

### Historical Dataset
Excel-imported reference data and coverage baseline. Used for coverage and future trend context.

### Benchmark/Ground Truth
Validation-only data for regression and quality scoring.

### Review History
Persistent human-in-the-loop workflow state.

### Operational Truth
The guarded dataset suitable for decision support. It must pass Data Guard and review/override rules.

## Web information architecture

```text
Command Center
 ├── Imports
 │    ├── Current Import
 │    ├── Snapshot Management
 │    └── Historical Imports
 ├── Quality
 │    ├── Missing Data
 │    ├── Guard Findings
 │    └── Coverage Context
 ├── Reviews
 │    ├── Open Reviews
 │    ├── Resolved Reviews
 │    └── Review Detail + Screenshot Evidence
 ├── Servers
 └── Exports / Reports
```

## Snapshot target architecture

Snapshots should become the default import container. A future import should not be “just the latest run”; it should belong to a named snapshot.

```text
Snapshot: S6 pre Transfer
 ├── screenshots
 ├── OCR report
 ├── ranking feeds
 ├── review queue
 ├── coverage status
 └── exports
```

## Guardrail

The UI may explain, link and collect review decisions, but it must not silently change Operational Truth.
