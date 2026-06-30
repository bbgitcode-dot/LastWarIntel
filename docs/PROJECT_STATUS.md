# Sentinel Project Status

**Current Version:** v0.9.5.27  
**Runtime Baseline:** v0.9.5.27 – Recoverable Gap Intelligence  
**Current Phase:** Operational Data Stability  
**Next Planned Sprint:** v0.9.5.27 – Field-Based Data Quality Loop

---

## Current summary

Sentinel has moved from OCR parser development into platform stabilization.

Recent work introduced:

- Command Center runtime UI.
- Operational import reporting.
- Ground Truth separation from runtime.
- Sentinel Data Guard.
- Sentinel Data Quality Loop.
- Safe quarantine as preferred fallback over silent correction.

The project is now focused on making imported data stable enough for strategic intelligence modules.

---

## What recent sprints tried to achieve

### v0.9.5.18 – Parser stabilization

Goal:

- Improve parser determinism.
- Introduce honest Ground Truth validation.
- Reduce bad matches and expose unresolved gaps instead of hiding them.

Outcome:

- Parser quality became measurable through precision, recall, F1, score, and category reports.
- Bad matches were reduced significantly.
- Gaps became visible and actionable.

---

### v0.9.5.19 – Command Center foundation

Goal:

- Move Sentinel from script-only workflow toward a web-based operations surface.

Outcome:

- FastAPI service foundation.
- Command Center UI.
- Imports and Data Quality views.
- Runtime health/status endpoints.

---

### v0.9.5.20 – Architecture consolidation

Goal:

- Remove direct Ground Truth dependency from Command Center runtime.
- Introduce repository/service boundary.

Outcome:

- Runtime no longer treats Ground Truth report as the application source of truth.
- Ground Truth remains benchmark/development tooling.

---

### v0.9.5.21 – Sentinel Data Guard

Goal:

- Prevent silent server assignment errors such as 551 screenshots being exported as Server 552.
- Show latest operational import data in the Command Center.

Outcome:

- Sentinel Data Guard Phase 1 introduced.
- Operational import report written to `data/latest_import_report.json`.
- Command Center reads current import data.

Finding:

- Guard behavior must be conservative. It must not silently repair or merge conflict blocks.

---

### v0.9.5.22 – Data Guard hotfix attempt

Goal:

- Fix the 551→552 block by using content-based evidence.

Outcome:

- False Server 552 output was removed.
- However, an overcorrection merged suspicious rows into Server 551.

Finding:

- Data Guard must not auto-merge conflict blocks.
- Correct response is quarantine and review/recovery, not forced reassignment.

---

### v0.9.5.23 – Sentinel Data Quality Loop

Goal:

- Add a recovery stage before review.
- Quarantine suspicious blocks safely.
- Avoid filename/timestamp logic.

Outcome:

- Server 552 disappeared from the latest 549/550/551 import test.
- Import report recognized exactly three servers: 549, 550, and 551.
- Data Guard reported healthy with no assignment warnings.
- Runtime increased significantly, showing the Quality Loop is active.

New finding:

- Rows from one ranking type can contaminate another ranking type.
- Example: THP-like rows appeared inside Alliance Power rankings.

Conclusion:

- Server assignment is no longer the only guard target.
- Sentinel needs a dedicated Ranking Guard.

---

## Current test observations

Latest large import:

- 52 screenshots.
- Servers: 549, 550, 551.
- 343 rows.
- Runtime: about 1382 seconds.
- No false 552 server in latest import report.
- Data Guard status: Healthy.
- Review count in report currently needs refinement because per-import review counters and overall review status can diverge.

Important issue found:

- Ranking type contamination: THP rows can appear inside Alliance Power export.

This is not a server assignment issue. It is a ranking integrity issue.

---

## Completed step: v0.9.5.25 – Sentinel Ranking Guard

Purpose:

> Prevent rows from entering the wrong ranking type.

Outcome:

- Ranking Guard introduced as a modular Data Guard component.
- THP-shaped rows in Alliance Power are quarantined.
- Alliance-shaped rows in THP are quarantined.
- Import report surfaces Ranking Guard quarantine as review work.

Expected checks:

### Alliance Power ranking

- Power values should generally be in alliance-scale ranges.
- Alliance name should be present or recoverable.
- Rows with THP-scale values should be rejected or quarantined.
- Ranking continuity should be plausible.

### Total Hero Power ranking

- Power values should generally be player-scale values.
- Player/alliance tag shape should be plausible.
- Rows with alliance-scale values should be rejected or quarantined.

### Generic checks

- Value range guard.
- Required field guard.
- Duplicate row guard.
- Rank continuity guard.
- Ranking-type confidence.
- Quarantine instead of auto-correction.

---

## Further stabilization backlog

## Next step: v0.9.5.26 – Field-Based Data Quality Loop

### v0.9.5.26 – Field-Based Data Quality Loop

Expand the Quality Loop beyond server/header recovery:

- Server Recovery.
- Alliance Tag Recovery.
- Player Name Recovery.
- Hero Power Recovery.
- Alliance Power Recovery.
- Rank Recovery.
- Ranking Type Recovery.

### v0.9.5.27 – Quarantine Center

Make quarantined rows visible and actionable in Command Center:

- Source screenshot.
- OCR evidence.
- Guard reason.
- Suggested recovery.
- Manual accept/reject workflow.

### v0.9.5.28 – Import Session Model

Introduce durable import sessions:

- import id,
- timestamp,
- server coverage,
- screenshots,
- rows,
- warnings,
- recovery attempts,
- quarantine results.

### v0.9.6.0 – Data Quality Baseline Release

Target:

- Stable import pipeline for 549/550/551.
- No silent server/ranking contamination.
- Measurable recovery and review rates.
- Command Center reflects operational truth.

---

## Current doctrine

```text
Data Guard protects.
Quality Loop recovers.
Ranking Guard validates semantic fit.
Quarantine preserves uncertainty.
Review is the final fallback.
```

Sentinel should prefer missing or quarantined data over false operational truth.


## Completed step: v0.9.5.26 – Ground Truth Validation Framework

Purpose:

> Make Sentinel import quality measurable against curated transfer-phase Ground Truth.

Outcome:

- Ground Truth validation now defaults to the active Server 551 Top 50 THP reference and current export.
- Precision is scoped to the Ground Truth server in multi-server imports.
- Ranking Guard quarantine evidence is included in validation reports.
- Detail rows now classify whether a row matched, was blocked by rank fallback, is missing, or is represented in quarantine.

This gives the Proud Owner a repeatable quality gate for S6 pre/post Transfer data.


## Completed step: v0.9.5.27 – Recoverable Gap Intelligence

Purpose:

> Resolve recoverable validation gaps without weakening Sentinel's integrity doctrine.

Outcome:

- Added same-server evidence resolver for Ground Truth validation.
- Unique exact THP power can now recover weak-identity rows such as UNKNOWN-name entries.
- Near-power recovery is allowed only with identity support.
- Server 551 Top 50 THP validation improved from 45 to 49 matched rows.
- Blocked rank fallbacks dropped from 5 to 1 while rank-only contradiction remains blocked.

This is the first operational inference layer: Sentinel now records when a row is observed, when a row is inferred for validation, and when uncertainty remains unresolved.


## v0.9.5.28 – Inference Engine Core

Sentinel now contains a first read-only Inference Layer. The Context Engine derives explainable validation conclusions from trusted neighboring evidence while keeping Operational Truth unchanged. This strengthens the path from guarded observations to strategic intelligence.
