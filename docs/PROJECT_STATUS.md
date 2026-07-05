# Project Status – Sentinel v0.9.5.101

**Current sprint:** v0.9.5.101 Character Crop Precision Guard  
**Primary objective:** Improve the precision of targeted Character ReOCR evidence for the 551 Gold Fidelity benchmark.

## Current state

The 551 pipeline remains structurally stable: recall is 100%, missing rows are 0, and bad matches are 0. v0.9.5.100 correctly separated alignment context gaps from true character drift. The remaining blocker is screenshot-faithful identity display: player names and alliance tags are still not exact enough for Gold Fidelity.

## v0.9.5.101 result

v0.9.5.101 tightens the evidence layer. It does not guess or canonicalize names. It improves crop placement and vote interpretation so Character ReOCR is less likely to read alliance tags, brackets, or neighbouring glyphs when it should verify a specific player-name or alliance-tag character.

## Still not Gold-ready

This patch does not claim that Server 551 is Gold-ready. It should reduce false/dirty evidence and make the next validator output more trustworthy. Gold remains blocked until expected glyph confirmations rise and unresolved/noisy crops shrink.

## Next focus

Run the 551 Ground Truth validator and compare:

- `character_reocr_verified_expected`
- `character_reocr_verified_observed`
- `character_reocr_unresolved`
- `player_name_display_drift_rows`
- `alliance_tag_display_drift_rows`

Priority examples remain `Joncollins21`/`Joncollinszl`, `[PbC]`/`[PBC]`, `PBC`/`PC`, `Mizzenmast`/`Mzzenmast`, and `Pumpkin G`/`Pumpkin 6`.
