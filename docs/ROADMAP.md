# Sentinel Roadmap

**Version:** v0.9.5.24

---

## Roadmap philosophy

Sentinel's roadmap is not a feature backlog. It is the path from raw screenshots to trusted strategic decision support.

Every milestone should help answer:

> **What deserves our attention today?**

---

## Current phase: Operational Data Stability

Goal:

> Make imported data trustworthy enough for intelligence.

Completed recently:

- Parser validation with Ground Truth.
- Command Center foundation.
- Ground Truth/runtime separation.
- Sentinel Data Guard.
- Sentinel Data Quality Loop.

Current focus:

- Stop silent data contamination.
- Build guardrails before strategic intelligence expands.

---

## Near-term milestones

### v0.9.5.24 – Documentation Consolidation

- Consolidate release notes.
- Update architecture and status documentation.
- Document operating model.
- Create Road to v1.0.

### v0.9.5.25 – Sentinel Ranking Guard

- Prevent THP rows from entering Alliance Power ranking.
- Prevent Alliance Power rows from entering THP ranking.
- Add ranking-type semantic checks.
- Quarantine instead of silent correction.

### v0.9.5.26 – Field-Based Data Quality Loop

- Expand recovery from server-only/header recovery to field-specific recovery.
- Add strategies for name, alliance tag, rank, THP, and alliance power.

### v0.9.5.27 – Quarantine Center

- Surface quarantined blocks in Command Center.
- Make review actionable and explainable.

### v0.9.5.28 – Import Session History

- Store import sessions with screenshots, runtime, rows, warnings, recoveries, and quarantine decisions.

### v0.9.6.0 – Data Stability Baseline

- Stable multi-server import for 549/550/551.
- Guarded server and ranking assignment.
- Review/Quarantine workflow visible in Command Center.

---

## Mid-term milestones

### Entity Resolution

- Track players across snapshots despite OCR noise.
- Improve alliance tag and player name normalization.
- Handle renames and transfer-like movements.

### Snapshot Repository

- Store trusted snapshots over time.
- Support historical comparisons.
- Support trend detection.

### Server Landscape

- Show server-level coverage and completeness.
- Identify missing rankings and stale snapshots.

### Recruitment Intelligence Calibration

- Use stable historical snapshots to calibrate recruitment value.
- Detect alliance instability and player availability over time.

---

## v1.0 target

Sentinel v1.0 should be production-ready for alliance leadership:

- Trusted import pipeline.
- Command Center with operational status.
- Entity pages for servers, alliances, and players.
- WatchTargets with history.
- Explainable strategic assessments.
- Recruitment Intelligence beyond MVP.
- Morning Briefing / Decision Center.

See `docs/ROAD_TO_V1.md`.
