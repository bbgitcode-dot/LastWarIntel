# ADR-0001: Layered Intelligence

Status: Accepted

## Context

Sentinel transforms observations into strategic intelligence. Mixing responsibilities makes explainability and testing difficult.

## Decision

Sentinel shall use a layered intelligence architecture.

Observation -> Snapshot -> Difference -> Fact -> Evidence -> Indicator -> Reasoning -> Assessment -> Value -> Recommendation

No layer may skip another layer.

## Consequences

Benefits:
- Explainable reasoning
- Deterministic processing
- Independent evolution of layers

Trade-offs:
- More components
- Additional transformation steps

## Alternatives Considered

- Flat analytics pipeline (rejected: poor explainability)
- Monolithic scoring engine (rejected: low maintainability)
