# Sentinel Data Guard

**Current release:** v0.9.5.137

## Principle

Evidence before inference. Inference before promotion. Promotion never modifies Operational Truth unless explicitly allowed by a future, guarded, auditable mechanism.

## v0.9.5.137 Guardrail

Character Acquisition Engine Phase I is evidence-only. It may score character observations, build consensus, and report weak positions, but it must not:

- rewrite player names,
- rewrite alliance tags,
- modify snapshots,
- modify Ground Truth,
- modify exports,
- bypass Ranking Guard or Promotion Guard.

The new `character_acquisition_report.json/xlsx` exists to improve explainability and future blocker resolution while preserving Data Guard invariants.
