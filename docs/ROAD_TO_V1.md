# Road to V1 – Sentinel v0.9.5.96

## Current Road

1. Stabilize one Gold benchmark server.
2. Extend the same fidelity discipline to more servers.
3. Only then scale acquisition to the full transfer group.
4. Only after full acquisition is reliable: entity intelligence, joiner/leaver detection, growth/decline analysis.

## Why This Changed

The latest 551 work proved that recall can be perfect while identity fidelity remains weak. Sentinel must not confuse these two qualities. A player can be matched by context and still be wrong as a reusable identity if the displayed name or alliance tag differs from the screenshot.

## v0.9.5.96 Milestone

v0.9.5.96 adds a Gold Fidelity Gate. It does not claim 551 is solved. It exposes the exact blockers that must be eliminated before a Gold Run is accepted.

## Next Milestone

v0.9.5.97 should implement actual targeted character re-OCR for the blocker rows now surfaced by the validator, starting with:

- `Joncollins21` vs `Joncollinszl`
- `PbC` vs `PBC`
- `PBC` vs `PC`
- mixed-script player-name suffix drift

The goal remains: one verified 551 Gold Run before wider scaling.
