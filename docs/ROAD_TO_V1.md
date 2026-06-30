# Road to Sentinel v1.0.0

> **From operational data stability to strategic decision support.**

**Created:** v0.9.5.24

---

## Current position

Sentinel has crossed the boundary from parser tool to operational platform.

Current assets:

- OCR import pipeline.
- Parser and normalizer.
- Ground Truth validator.
- Command Center.
- Operational import report.
- Sentinel Data Guard.
- Sentinel Data Quality Loop.

Current limiting factor:

> **Data stability must be strong enough before intelligence expands.**

---

## Milestone 1 – Data Integrity Fortress

Target versions: v0.9.5.25 – v0.9.6.0

### Goals

- No silent server contamination.
- No silent ranking-type contamination.
- Clear quarantine path.
- Review as an explicit workflow.
- Command Center reflects current operational truth.

### Required capabilities

- Sentinel Ranking Guard.
- Field-based Data Quality Loop.
- Quarantine Center.
- Import Session History.
- Stable import report schema.

### Exit criteria

- Large imports across 549/550/551 show no false server output.
- THP rows do not enter Alliance Power rankings.
- Alliance rows do not enter THP rankings.
- Quarantined rows are visible and explainable.
- Review actions are specific and actionable.

---

## Milestone 2 – Historical Data Foundation

Target versions: v0.9.6.x

### Goals

- Persist trusted snapshots.
- Create stable server/alliance/player identities.
- Prepare trend analysis.

### Required capabilities

- Snapshot repository.
- Import session table.
- Player identity resolution.
- Alliance identity resolution.
- Deduplication and snapshot replacement rules.

### Exit criteria

- Sentinel can compare two imports from the same server.
- Sentinel can track a player despite minor OCR name noise.
- Sentinel can detect joined/left/moved players.

---

## Milestone 3 – Operational Intelligence

Target versions: v0.9.7.x

### Goals

- Transform stable differences into facts.
- Surface what changed overnight.
- Create operational WatchTargets.

### Required capabilities

- Difference detection from trusted snapshots.
- Intelligence facts.
- WatchTarget enrichment.
- Server and alliance overview pages.

### Exit criteria

- Sentinel can say what changed between imports.
- Every change is traceable to source observations.
- Command Center highlights important operational changes.

---

## Milestone 4 – Strategic Assessments

Target versions: v0.9.8.x

### Goals

- Convert facts and indicators into explainable assessments.

### Candidate assessments

- Recruitment Window.
- Alliance Collapse Risk.
- Leadership Risk.
- Whale Migration.
- Transfer Winner.
- Transfer Loser.
- Hidden Opportunity.

### Exit criteria

- Assessments expose evidence, indicators, reasoning, and confidence.
- No assessment is generated from untrusted or quarantined data.

---

## Milestone 5 – Decision Center

Target versions: v0.9.9.x → v1.0.0

### Goals

- Turn assessments into prioritized recommendations.
- Make Sentinel useful for daily leadership decisions.

### Required capabilities

- Morning Briefing.
- Priority queue.
- Recommendation history.
- Decision snapshots.
- Reports.
- Watchlist workflows.

### Exit criteria for v1.0.0

Sentinel v1.0.0 is ready when the Proud Owner can open the Command Center and answer within a few minutes:

- What changed?
- Can I trust the data?
- What needs review?
- Which opportunity matters most?
- What should leadership do next?

---

## v1.0.0 definition

Sentinel v1.0.0 is not defined by feature count.

It is defined by trust:

> **Trusted observations create trusted intelligence. Trusted intelligence supports better human decisions.**


## v0.9.5.28 – Inference Engine Core

Sentinel now contains a first read-only Inference Layer. The Context Engine derives explainable validation conclusions from trusted neighboring evidence while keeping Operational Truth unchanged. This strengthens the path from guarded observations to strategic intelligence.
