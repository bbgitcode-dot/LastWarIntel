# Patch Summary – v0.9.5.104

## Sentinel v0.9.5.104 – Character Geometry & Tag Fidelity Guard

This sprint responds to the v0.9.5.103 validation finding: the remaining blocker is not row matching, but pixel geometry inside the identity field.

### What changed

- Player-name ReOCR crops for visible-window screenshots now stay left of the power column.
- Alliance-tag ReOCR crops are tighter and more centered on the requested tag glyph.
- Power-like OCR votes from player-name crops are classified as `crop_power_column_bleed`.
- Character ReOCR remains conservative and evidence-only.

### Why this matters

`Joncollins21` must not become `Joncollinszl`, and `PbC` must not silently normalize to `PBC`. Sentinel needs exact identity, not approximate identity, before long-term joiner/leaver/growth tracking can be trusted.

### Version

`0.9.5.104`
