# Road to Sentinel v1.0.0

> From screenshot import to trusted strategic decision support.

**Current Version:** v0.9.5.51  
**Current Phase:** Data Integrity Fortress

---

## North Star

Sentinel v1.0.0 is ready when alliance leadership can open the Command Center and quickly answer:

- What changed?
- Can I trust the data?
- What still needs review?
- Which opportunity deserves attention?
- What should we do next?

---

## Milestone 1 – Data Integrity Fortress

**Target:** v0.9.5.x → v0.9.6.0  
**Status:** Active

### Goal

Make screenshot-derived data safe enough to become Operational Truth.

### Completed capabilities

- OCR provider architecture.
- Parser and ranking row extraction.
- Ground Truth validation framework.
- Command Center foundation.
- Runtime import report.
- Sentinel Data Guard.
- Sentinel Data Quality Loop.
- Ranking Guard.
- Source-local Power Sanity Guard.
- Leading-digit Power Recovery metadata.

### Remaining capabilities

#### v0.9.5.47 – Context-aware Power Candidate Recovery

Status: Completed.

Delivered:

- Candidate scoring engine for suspicious THP and Alliance Power values.
- Candidate metadata on recovered and ambiguous rows.
- Server 553 regression coverage, including a context case where `764M` recovers to `224M` instead of the legacy `164M`.

#### v0.9.5.48 – Source Context Recovery Reportability

Status: Completed.

Delivered:

- Excel export metadata for recovered and ambiguous power candidates.
- Import-report candidate traces with selected value, best/second score, margin, confidence, and reason.
- Corrected global review-count aggregation.

#### v0.9.5.51 – Import Session and Segment Integrity

Create explicit import sessions and ranking-session metadata.

Exit criteria:

- Screenshot sets can be grouped without trusting filename order.
- Missing, duplicate, and mixed ranking segments are visible.
- Segment continuity warnings are explainable.

#### v0.9.5.51 – Quarantine Center Foundation

Make review visible and actionable in the Command Center.

Exit criteria:

- Every quarantined row shows screenshot, reason, suspected field, and next action.
- Human review can accept, reject, or mark for recovery.

#### v0.9.6.0 – Data Stability Baseline

Declare a baseline only after repeated 549–553 regression runs are stable.

Exit criteria:

- No silent server contamination.
- No silent ranking-type contamination.
- No unrecovered false 7xxM/77B values in Operational Truth.
- Ground Truth Server 551 remains stable.
- Reports distinguish clean, recovered, and quarantined rows.

---

## Milestone 2 – Historical Data Foundation

**Target:** v0.9.6.x

### Goal

Persist trusted snapshots and make changes measurable.

### Required capabilities

- Snapshot repository.
- Import session table.
- Player identity resolution.
- Alliance identity resolution.
- Deduplication and replacement rules.
- Snapshot comparison by server, alliance, player, and ranking type.

### Exit criteria

- Sentinel can compare two trusted imports from the same server.
- Sentinel can track a player despite minor OCR name noise.
- Sentinel can identify joined, left, moved, and renamed entities with evidence.

---

## Milestone 3 – Operational Intelligence

**Target:** v0.9.7.x

### Goal

Turn trusted differences into operational facts.

### Required capabilities

- Difference detection.
- Fact generation.
- WatchTarget model.
- Server and alliance overview pages.
- Change severity scoring.

### Exit criteria

- Sentinel can state what changed since the last trusted snapshot.
- Every change is traceable to source observations.
- Command Center highlights important operational changes.

---

## Milestone 4 – Strategic Assessments

**Target:** v0.9.8.x

### Goal

Convert facts and indicators into explainable assessments.

### Candidate assessments

- Recruitment window.
- Alliance collapse risk.
- Whale movement.
- Transfer opportunity.
- Transfer risk.
- Hidden alliance instability.

### Exit criteria

- Assessments include evidence, reasoning, confidence, and recommended action.
- No assessment is generated from untrusted or quarantined data.

---

## Milestone 5 – Decision Center

**Target:** v0.9.9.x → v1.0.0

### Goal

Make Sentinel useful for daily leadership decisions.

### Required capabilities

- Morning Briefing.
- Priority queue.
- Recommendation history.
- Decision snapshots.
- Watchlist workflows.
- Exportable leadership reports.

### v1.0.0 definition

Sentinel v1.0.0 is not defined by feature count. It is defined by trust.

> Trusted observations create trusted intelligence. Trusted intelligence supports better human decisions.

