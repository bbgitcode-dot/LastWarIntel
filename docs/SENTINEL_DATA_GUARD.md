# Sentinel Data Guard – v0.9.5.96 Addendum

## Gold Fidelity Gate

Data Guard now distinguishes protected Operational Truth from Gold Fidelity. A row can be protected and matched while still blocking Gold status because its displayed identity is not exact.

## Rules

- Cache remains disabled during data-quality validation unless the Proud Owner explicitly enables it.
- Screenshot truth overrides filename, upload order, fuzzy matching and historical assumptions.
- Fuzzy identity may help review prioritization but never creates Operational Truth.
- Alliance tags are case-sensitive.
- Stable but confusable characters are not blockers by default; actual drift is.

## Current Objective

Produce one Server 551 run where player names, alliance tags, rank and power match the screenshots exactly.
