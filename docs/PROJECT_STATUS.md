# Project Status – Sentinel v0.9.5.99

**Current sprint:** v0.9.5.99 Character Re-OCR Provider Input Fix  
**Primary objective:** Make targeted Character Verification evidence actually run in the normal 551 Gold Fidelity validation path.

## Current state

The import pipeline remains stable for Server 551: recall is 100%, missing rows are 0, bad matches are 0. The remaining blocker is Gold Fidelity: player display names and alliance tags are not yet screenshot-exact.

## v0.9.5.99 result

v0.9.5.99 fixes the activation gap from v0.9.5.97. Character Verification candidates no longer stay dormant when screenshots are available. The validator can auto-discover screenshots, including `551.zip`, and emits target evidence even when the OCR provider is not available in the validation environment.

## Still not Gold-ready

This patch does not claim that Server 551 is now Gold-ready. It makes the next bottleneck measurable: targets are emitted and can be verified/unresolved rather than silently counted as zero.

## Next focus

Use real OCR-provider output on the targeted crops to increase `character_reocr_verified_expected` for high-value rows, starting with:

- `Joncollins21` vs `Joncollinszl`
- `PbC` vs `PBC`
- `Pumpkin G` vs `Pumpkin 6`
- short tags with missing or case-drifted glyphs
