# ADR-0004 – Assessment Engine

Status: Accepted

## Context
Strategic assessments must be deterministic, explainable and reusable.

## Decision
A generic Assessment Engine evaluates Facts, Evidence, Indicators and Reasoning rules to produce immutable Assessments.

Assessments contain results only; evaluation logic resides in the engine.

## Consequences
- New assessments are implemented as rules.
- Infrastructure remains unchanged when adding new intelligence modules.
- Assessments are reproducible.
