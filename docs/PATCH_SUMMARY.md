
# Patch Summary – v0.9.5.95

## Sentinel v0.9.5.95 – Targeted Character Verification Planning

This sprint follows the v0.9.5.94 Identity Fidelity report. It acknowledges that fuzzy identity resolution is not safe for Operational Truth: a real player named `Joncollinszl` could exist. The safe path is not canonicalization, but targeted re-reading of suspicious characters from the screenshot.

### Delivered

- New character-risk helper: `parser/character_verification.py`.
- Validator-level targeted verification candidates for player names and alliance tags.
- Case-sensitive alliance-tag verification planning.
- New summary metrics and Excel/JSON report sections.
- Regression tests for `Joncollins21` vs `Joncollinszl` and `PbC` vs `PBC`.

### Non-goals

- No automatic correction of player names.
- No fuzzy canonicalization of alliance tags.
- No joiner/leaver logic based on fuzzy identity.

### Version

`0.9.5.95`
