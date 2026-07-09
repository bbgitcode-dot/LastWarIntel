# v0.9.5.141 – Character Position Intelligence Phase I

- Implements functional Character Position Intelligence in the validator, not just report scaffolding.
- Adds `character_position_intelligence_report.json/xlsx` with position-level risk, action, and rank-level acquisition focus.
- Feeds weak/critical position decisions into the Evidence Scheduler so Gold Accuracy prioritizes problematic character positions.
- Keeps Display Reconstruction, Strike clearance, Context Gaps, and Operational Truth read-only.
- Report phase label: `v0.9.5.141_character_position_intelligence`.

# v0.9.5.140 – Gold Regression & Strike II

- Adds permanent GC-001 Joncollins21 Gold-Core regression metadata.
- Extends Gold-Core elimination with Strike II: one missing Latin glyph plus optional known local glyph confusion, only when Rank/Power/Core Alliance anchors are proven.
- Keeps context gaps read-only and never modifies Operational Truth.
- Report phase label: `v0.9.5.140_gold_regression_strike_ii`.

# Road to V1 – Sentinel

**Current release:** v0.9.5.141  
**Current line:** Gold Accuracy / Character Evidence Acquisition

## Near-term milestones

| Version | Milestone | Goal |
|---|---|---|
| v0.9.5.140 | Gold Core Elimination Phase I | Convert Character ReOCR fragments into scored, explainable consensus evidence. |
| v0.9.5.140 | Multi-Crop Consensus | Generate multiple observations per weak glyph position and improve evidence coverage. |
| v0.9.5.140 | Glyph Similarity Memory | Track recurring glyph confusions such as `2/Z`, `1/l/I`, Hangul/Han substitutions. |
| v0.9.5.140 | Gold Blocker Elimination | Treat the remaining Gold-Core blockers as an explicit engineering backlog. |
| v0.9.5.141 | Gold Regression | Regression over 551 and the broader 549–554 evidence set. |
| v0.9.5.142 | V1 Candidate Prep | Freeze guardrails, docs, and operational mode for a V1 candidate. |

## V1 principle

Runtime is secondary during the Gold Accuracy phase. The target is a highly accurate and explainable data state, with Data Guard preventing unsupported promotion into Operational Truth. Performance optimization should follow after Gold Fidelity stabilizes.


| v0.9.5.140 | Gold Blocker Strike I | Clear the first narrow localized Latin glyph blocker under strict evidence guardrails. |
