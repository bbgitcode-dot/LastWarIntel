# Sentinel Roadmap

**Version:** v0.9.5.58

## Current focus

Review Quality is now moving from explanation to human-in-the-loop resolution. v0.9.5.58 added human-readable review problem statements, candidate choices, and persistent review history groundwork.

## Next

- v0.9.5.59: Review Resolution Model
- v0.9.5.60: Editable Review Dashboard
- v0.9.5.61: Manual Override Engine

# Sentinel Roadmap

**Version:** v0.9.5.57

## Current phase: Data Integrity Fortress / Evidence-Driven Review

Recent milestone: v0.9.5.57 binds review evidence cards to the underlying recovery traces, including ambiguous candidate lists and margins. This makes individual review items explainable without opening raw JSON.

Next planned direction:

- Add crop/visual assets for each evidence item.
- Integrate `review_evidence_pack.html` as a detail view reachable from the broader Command Center click path.
- Design Manual Review Resolution with audit-safe overrides before making any UI editable.
- Keep Command Center high-level and Evidence Pack item-centered.

---

# Sentinel Roadmap

**Version:** v0.9.5.56

## Current phase: Data Integrity Fortress / Review Quality

Recent milestone: v0.9.5.56 adds a focused Review Evidence Pack so individual quarantined or ambiguous rows can be reviewed without scanning the full Command Center.

Next planned direction:

- Generate row/power/name crop assets for each evidence card.
- Add zoomable visual links from the Evidence Pack to review crops.
- Keep Command Center high-level and keep review work item-centered.
- Continue keeping Data Quality ahead of Intelligence.

---

# Sentinel Roadmap

**Version:** v0.9.5.55

## Current phase: Data Integrity Fortress / Operational Observability

Recent milestone: v0.9.5.55 adds a static Command Center and Review Dashboard so every run can be assessed visually from report artifacts.

Next planned direction:

- Review Center with row/image crops and zoomable evidence.
- Better separation of dangerous quarantine, ambiguous recovery, and human-review-needed items.
- Continue keeping Data Quality ahead of Intelligence.

---

# Sentinel Roadmap

**Version:** v0.9.5.52

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

### v0.9.5.51 – Import Session and Segment Integrity

- Introduce explicit import sessions.
- Detect missing, duplicate, mixed, and out-of-order segments.
- Avoid filename/order assumptions.

### v0.9.5.51 – Quarantine Center Foundation

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

