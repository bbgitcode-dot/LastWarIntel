# Sentinel Architectural Decisions

**Current version:** v0.9.5.72

This file is the current canonical architectural-decision summary. The `/docs/ADR` directory contains historical ADRs and currently has duplicate numbering from earlier sprints; those files should be renumbered or superseded in a future documentation cleanup.

## ADR-001 – Screenshot order is not truth

Screenshot filename, order, upload order and timestamp order must never be treated as authoritative. Runtime reconstruction must rely on intrinsic evidence: server evidence, ranking type, row shape, rank, power continuity and source-local context.

## ADR-002 – Ground Truth validates Sentinel but does not power runtime

Ground Truth and benchmarks are development tools. They must not drive runtime Command Center, Quality, Operational Readiness or exports.

## ADR-003 – Data Guard protects Operational Truth

Data Guard may validate, warn, quarantine or block. It may not guess. Uncertain evidence must be recovered with strong evidence or moved to review/quarantine.

## ADR-004 – Ranking Guard validates semantic fit

`alliance_power` and `total_hero_power` have different scales, fields and row shapes. Ranking-type contamination is a data-integrity issue.

## ADR-005 – Recovery must preserve original evidence

Context-aware power recovery may suggest or promote candidates only under explicit confidence rules. Original OCR values, candidate list, scores and reasons must remain reportable.

## ADR-006 – Human Review is an audit workflow

Resolving a review does not automatically rewrite Operational Truth. It records a human decision, comment and selected candidate/manual value. A future Manual Override Engine may consume those decisions under Data Guard control.

## ADR-007 – UI is an observability and workflow layer, not a truth source

Command Center, Imports, Quality and Reviews read report/history/database artifacts. They must not silently re-score, re-rank or promote data.

## ADR-008 – Current, Historical and Benchmark contexts are separate

Sentinel must keep current run, review history, historical dataset and benchmark/ground-truth outputs separate. Cross-contamination produces misleading operational status.

## ADR-009 – Historical data is reference coverage

Historical Excel imports provide baseline coverage and temporal context. They do not overwrite runtime Operational Truth and should be clearly labelled as historical/reference data.

## ADR-010 – Snapshot is the future import container

A Snapshot is a human-named container for one event/phase of data collection. Future screenshot uploads, reviews, exports and coverage should be bound to an active snapshot.

Example snapshots:

- S5 pre Transfer
- S5 post Transfer
- S5 Gold Vein
- S6 pre Season
- S6 pre Transfer

## ADR-011 – Data Quality before Intelligence

The Intelligence layer should not be expanded until import, review, snapshot and quality gates are reliable. Strategy built on unstable data creates false confidence.

## Open architectural decisions

- How resolved reviews become guarded export corrections.
- Whether snapshots are JSON-backed, SQLite-backed or hybrid long term.
- How screenshot upload UI enforces active snapshot selection.
- How historical server/alliance/player timelines are normalized across name changes and alliance transfers.
- How ADR numbering in `/docs/ADR` should be cleaned without losing history.


## ADR – v0.9.5.73 Snapshot import binding is mandatory

Screenshot imports must have an active managed `screenshot_upload` snapshot. A missing, closed, complete or wrong-type snapshot blocks import instead of allowing evidence to enter the Current Run without phase context. This prevents accidental mixing of events such as `S6 pre Transfer` with another phase. Snapshot metadata is audit context only and never overrides Data Guard, Ranking Guard or Human Review.
