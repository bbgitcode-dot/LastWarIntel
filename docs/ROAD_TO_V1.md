# Road to V1 – Sentinel

**Current release:** v0.9.5.137  
**Current line:** Gold Accuracy / Character Evidence Acquisition

## Near-term milestones

| Version | Milestone | Goal |
|---|---|---|
| v0.9.5.137 | Character Acquisition Engine Phase I | Convert Character ReOCR fragments into scored, explainable consensus evidence. |
| v0.9.5.138 | Multi-Crop Consensus | Generate multiple observations per weak glyph position and improve evidence coverage. |
| v0.9.5.139 | Glyph Similarity Memory | Track recurring glyph confusions such as `2/Z`, `1/l/I`, Hangul/Han substitutions. |
| v0.9.5.140 | Gold Blocker Elimination | Treat the remaining Gold-Core blockers as an explicit engineering backlog. |
| v0.9.5.141 | Gold Regression | Regression over 551 and the broader 549–554 evidence set. |
| v0.9.5.142 | V1 Candidate Prep | Freeze guardrails, docs, and operational mode for a V1 candidate. |

## V1 principle

Runtime is secondary during the Gold Accuracy phase. The target is a highly accurate and explainable data state, with Data Guard preventing unsupported promotion into Operational Truth. Performance optimization should follow after Gold Fidelity stabilizes.
