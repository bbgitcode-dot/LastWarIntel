# Handoff Next Chat – Sentinel v0.9.5.93

## Baseline

Use:

```text
Sentinel_v0.9.5.93.zip
```

## Current state

v0.9.5.93 follows the Server 551 v0.9.5.92 validation. Accepted rows now export cleanly and `PENDING REVIEW` placeholders are filtered from normal Operational Truth sheets and console summaries. Quarantine/review evidence remains available in the dedicated review surfaces.

The new strategic data-quality focus is Identity Fidelity: exact alliance tags and player names matter for historical transfer intelligence. Fuzzy matching can help review, but it cannot be allowed to silently mutate Operational Truth.

## Next recommended sprint

**v0.9.5.94 – Identity Fidelity Regression & Alliance Tag Case Sensitivity**

Focus:

- Create targeted regression cases for `Joncollins21` vs `Joncollinszl`.
- Create alliance-tag case-sensitivity tests such as `DAY` vs `daY`.
- Improve Identity Guard reporting in export/review dashboards.
- Run Server 551 again and confirm Recall remains 1.0 while review rows no longer appear as ranks 102-105.
- Then run Server 552 Alliance Power as the next screenshot-based benchmark.

## Rules

- Screenshot is Ground Truth.
- Cache off for benchmark validation.
- No Intelligence features until DataGuard and Identity Guard are stable.
- Do not treat upload order, filename order, console output or fuzzy match score as truth.
