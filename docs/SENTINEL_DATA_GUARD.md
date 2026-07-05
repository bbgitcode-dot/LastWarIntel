# Sentinel Data Guard – v0.9.5.102 Addendum

## DataGuard rule

DataGuard protects Operational Truth. It may collect evidence, mark uncertainty and require review, but it must not silently rewrite player or alliance identities.

## Character ReOCR status

Character ReOCR remains evidence-only. It can support validation, but it does not currently overwrite Operational Truth.

v0.9.5.102 adds per-target debug evidence so the team can determine why a target did or did not verify:

- row slot;
- crop box;
- crop strategy;
- target glyph;
- vote outputs;
- selected glyph;
- final status.

## Alignment guard remains mandatory

Rows marked as alignment context gaps must not enter Character Verification. A mismatch such as `K9 Thunder` vs `YUNS` is an alignment/context problem, not a glyph problem.

## Current next step

Use the debug report to choose the next fix. Do not promote Character ReOCR output to Operational Truth until the evidence path is proven on 551.
