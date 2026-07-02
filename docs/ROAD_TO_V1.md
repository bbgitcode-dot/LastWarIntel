# Road to Sentinel v1.0.0

**Current version:** v0.9.5.74  
**Current phase:** Data Integrity Fortress → Snapshot Management Hardening  
**North Star:** Explainable strategic intelligence for Last War alliance leadership.

## North Star

Sentinel v1.0.0 is ready when alliance leadership can open the Command Center and answer:

- What data do we have?
- Can we trust it?
- What changed since the last snapshot?
- What needs human review?
- Which servers, alliances or players are strategically relevant?
- What action is recommended and why?

## Phase 1 – Operational Truth Foundation

**Status:** Largely complete.

Delivered:

- OCR provider architecture.
- Parser and ranking extraction.
- Data Guard.
- Ranking Guard.
- Power Sanity Guard.
- Context-aware power recovery.
- Quarantine and Review queues.
- Ground Truth validator.
- Import reports and Excel export.

Principle:

> No false Operational Truth. Uncertain evidence must recover, review or quarantine.

## Phase 2 – Data Integrity Fortress

**Status:** Active.

Goal: reduce the remaining OCR/upload/data-quality risk before building Intelligence.

Delivered:

- Review Evidence Pack.
- Persistent Review History.
- Explainable review problem statements.
- Candidate choices and explainability steps.
- Screenshot preview and rank highlight overlay.
- Operational Readiness dashboard.
- Historical import and coverage drilldown.

Remaining:

- Snapshot close/freeze semantics.
- Screenshot quality preflight.
- Duplicate screenshot detection.
- Row geometry and crop confidence.
- Manual Review Override Engine under Data Guard control.
- Clear snapshot-level completeness gates.

## Phase 3 – Snapshot Management

**Status:** Upload binding enforced in v0.9.5.73; close/freeze and comparison still planned.

Snapshots become the primary temporal container:

```text
Snapshot
 ├── Screenshots
 ├── OCR evidence
 ├── Ranking feeds
 ├── Review items
 ├── Historical coverage
 ├── Exports
 └── Operational status
```

Required milestones:

1. Create Snapshot in Import Center. ✅
2. Active Snapshot required for screenshot upload/import. ✅
3. Snapshot-level coverage and missing-feed report. ✅
4. Snapshot-level review queue binding. ✅
5. Snapshot close/freeze semantics.
6. Snapshot compare foundation.

Example:

```text
S5 pre Transfer
S5 post Transfer
S5 Gold Vein
S6 pre Season
S6 pre Transfer
```

## Phase 4 – Historical Intelligence

**Status:** Planned after Data Integrity and Snapshot Management.

Goal: make time visible.

Milestones:

- Server historical timeline.
- Alliance historical timeline.
- Player historical timeline.
- Snapshot-to-snapshot diff.
- Growth/decline detection.
- Server completeness over time.

Questions Sentinel should answer:

- Which servers grew since the last snapshot?
- Which alliances changed rank?
- Which players changed alliance?
- Which data is stale or missing?

## Phase 5 – Assessment Engine

**Status:** Existing prototype/architecture exists; strategic activation should wait until data integrity is reliable.

Goal: convert observed data into explainable strategic assessments.

Milestones:

- Threat scoring.
- Opportunity scoring.
- Transfer-value analysis.
- Server strength classification.
- Alliance stability assessment.
- Explainability trace for every assessment.

## Phase 6 – Recommendation Engine

**Status:** Planned.

Goal: turn assessments into decision support.

Examples:

- Which server should be scouted next?
- Which alliance is a transfer candidate?
- Which missing screenshot gives the biggest confidence gain?
- Which review blocks the most important server?

## V1.0.0 Definition

Sentinel reaches v1.0.0 when:

- Operational Truth is guarded and explainable.
- Snapshot workflow is enforced.
- Historical and current data are separated and comparable.
- Review workflow is auditable.
- Command Center provides operational and strategic status.
- Intelligence recommendations are evidence-backed and explainable.
- The platform can be handed to alliance leadership without requiring developer interpretation of JSON, OCR logs or raw Excel files.

## Near-term roadmap

### v0.9.5.73 candidate – Snapshot Upload Binding
- Require/select active snapshot before screenshot import.
- Bind current import report and review history to snapshot id/name.
- Show snapshot-level feed completeness.

### v0.9.5.74 candidate – Screenshot Quality Preflight
- Detect low-quality screenshots before OCR.
- Flag wrong orientation, cropped ranking area, duplicate upload and unreadable power column.

### v0.9.5.75 candidate – Manual Override Guardrails
- Allow resolved reviews to produce guarded export corrections.
- Preserve original OCR evidence and reviewer audit trail.

### v0.9.6.0 candidate – Data Integrity Fortress Freeze
- Stabilize import, review, snapshot and quality gates before deeper intelligence work.
