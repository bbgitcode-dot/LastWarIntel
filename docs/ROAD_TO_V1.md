# Road to V1 – Sentinel v0.9.5.102

## V1 principle

Sentinel must not become an intelligence platform until its Operational Truth is stable. Player and alliance tracking over time requires screenshot-faithful identities, including case-sensitive alliance tags and exact player display names.

## Current phase: 551 Gold Fidelity

The current goal is not full 128-server intelligence. The current goal is to prove one benchmark server can be validated with full data-quality visibility.

## Recent milestones

- v0.9.5.100 separated alignment context gaps from character drift.
- v0.9.5.101 attempted crop/vote precision improvements.
- v0.9.5.102 adds Character ReOCR debug instrumentation because the previous crop changes did not materially improve the result.

## Required path to V1

1. 551 Gold Fidelity diagnostics.
2. 551 Character ReOCR correction based on debug evidence.
3. 551 Gold Fidelity pass criteria.
4. Multi-server acquisition stability.
5. Full snapshot completeness reporting.
6. Entity Intelligence only after stable acquisition and identity fidelity.

## Current blocker

Character ReOCR currently generates many targets but leaves too many unresolved. The next patch must be selected based on `character_reocr_debug_report`, not guesswork.

## v0.9.5.103 Update – ReOCR Row Slot & Field Anchor Correction

The v0.9.5.102 debug reports proved that Character ReOCR failures are mostly localization failures, not raw OCR failures. v0.9.5.103 therefore adds 551-window screenshot row geometry and explicit crop-anchor diagnostics so future runs can separate wrong-row/wrong-field crops from true character-recognition misses. Operational Truth remains unchanged; ReOCR remains evidence-only.

## v0.9.5.104 – Gold Fidelity prerequisite

Before v1.0.0, Sentinel must prove exact identity from screenshots. v0.9.5.104 moves toward that by tightening character-level crop geometry for player names and alliance tags. This is a prerequisite for reliable season-over-season identity tracking, especially for case-sensitive alliance tags and high-value players.

## v0.9.5.105 – Gold Fidelity prerequisite

Gold Fidelity requires exact player and alliance identity, not normalized similarity. v0.9.5.105 addresses the most concrete high-value blocker (`Joncollins21` / `[PbC]`) by improving character-crop localization before any identity correction is attempted. This keeps the V1 path focused on proof-first OCR: correct row, correct field, correct glyph, then and only then verified identity.

## v0.9.5.106 – Gold Fidelity prerequisite

The path to v1.0.0 now requires calibrated character evidence rather than fixed character crops. v0.9.5.106 adds candidate-crop search and records candidate reasons so high-value blockers such as `Joncollins21` and `[PbC]` can be diagnosed as pixel-localization problems instead of being treated as OCR model failures. The next milestone is to validate that the calibration raises expected-character verification without increasing observed/noise confirmations.


## v0.9.5.107 – Telemetry checkpoint

Before scaling Gold Fidelity beyond the 551 benchmark, Sentinel needs explainable runtime behavior. v0.9.5.107 adds timing telemetry at validator and Character ReOCR target level. The next milestone is to use this report to reduce repeated OCR calls without re-enabling cache prematurely, while continuing to harden alliance-tag case fidelity.
