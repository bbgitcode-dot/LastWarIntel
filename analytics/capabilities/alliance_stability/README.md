# Alliance Stability Capability

The Alliance Stability capability contains strategic assessment rules that detect structural instability in alliances.

## Current Rules

- `RecruitmentWindowRule`
- `AllianceCollapseRule`

## Design

Rules receive a complete `AssessmentContext`. They do not load repositories, mutate state, perform presentation work or call other rules directly.

The generic Assessment Engine remains domain-neutral. Alliance-specific knowledge lives in this capability package.
