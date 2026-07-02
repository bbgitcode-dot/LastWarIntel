# Sentinel Roadmap

**Version:** v0.9.5.50

---

## Roadmap philosophy

Sentinel's roadmap is the path from raw screenshots to trusted strategic decision support.

Every milestone should help answer:

> What deserves our attention today?

---

## Current phase: Data Integrity Fortress

Goal:

> Make imported data trustworthy enough for intelligence.

Completed recently:

- Ground Truth validation framework.
- Command Center foundation.
- Ground Truth/runtime separation.
- Sentinel Data Guard.
- Data Quality Loop.
- Ranking Guard.
- Power Sanity Guard.
- Source-local Power Digit Recovery.
- Documentation consolidation and handoff package.

Current focus:

- Validate context-aware power candidate recovery in Server 549–553 regression behavior.
- Introduce explicit import sessions and segment integrity.
- Keep recovery explainable and audit-ready.
- Build guardrails before strategic intelligence expands.

---

## Near-term milestones

### v0.9.5.47 – Context-aware Power Candidate Recovery

Completed in v0.9.5.47.

- Generates multiple recovery candidates for suspicious power values.
- Scores candidates using source-local ranking context.
- Recovers clear candidates and preserves candidate metadata.
- Keeps ambiguous values reviewable.

### v0.9.5.48 – Source Context Recovery Reportability

Completed in v0.9.5.48.

- Exposes candidate scoring in Excel exports.
- Adds candidate traces to the import report.
- Fixes review-count aggregation.

### v0.9.5.50 – Import Session and Segment Integrity

- Introduce explicit import sessions.
- Detect missing, duplicate, mixed, and out-of-order segments.
- Avoid filename/order assumptions.

### v0.9.5.50 – Quarantine Center Foundation

- Surface quarantined rows in Command Center.
- Include source screenshot, field, reason, and proposed action.

### v0.9.6.0 – Data Stability Baseline

- Stable multi-server import for Server 549–553 regression data.
- No silent server or ranking-type contamination.
- Explainable recovery and quarantine states.

---

## Mid-term milestones

### Historical Data Foundation

- Snapshot repository.
- Import session history.
- Player and alliance identity resolution.
- Snapshot comparison.

### Operational Intelligence

- Difference detection.
- WatchTargets.
- Server and alliance change views.
- Priority signals.

### Strategic Assessments

- Recruitment window.
- Whale movement.
- Alliance instability.
- Transfer opportunity.
- Explainable confidence and evidence.

### Decision Center

- Morning Briefing.
- Priority queue.
- Recommendation history.
- Leadership reports.

