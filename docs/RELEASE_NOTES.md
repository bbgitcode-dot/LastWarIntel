## v0.9.5.96 – 551 Gold Fidelity Gate

v0.9.5.96 introduces a stricter Gold Fidelity validation layer for the Server 551 benchmark. The sprint does not improve performance and does not enable cache. It makes the remaining screenshot-fidelity blockers explicit so the next OCR work can target the exact rows and characters that prevent a 100% trusted run.

### Added

- `gold_fidelity_ready` summary flag.
- `gold_fidelity_blocker_rows` summary metric.
- `player_name_display_drift_rows`, `alliance_tag_display_drift_rows`, `power_display_drift_rows`, and `rank_display_drift_rows`.
- `gold_fidelity_blockers` JSON section and Excel sheet.
- Smoke tests for case-sensitive alliance tags and exact player-name character drift.

### Changed

- Character verification no longer treats a perfectly matching but OCR-confusable character as a default blocker. Example: `LOVE BIEN` is not flagged just because it contains `O`, `B`, or `I`.
- Character verification now focuses on actual screenshot-fidelity drift by default. Exploratory stable-glyph scanning remains possible by opt-in argument.

### Data Guard Position

- Cache remains disabled for validation.
- Fuzzy/normalized identity remains intelligence support only, never Operational Truth.
- Alliance tags remain case-sensitive identifiers.
- Quarantine remains preferred over false Operational Truth.

### Validation

```text
5 passed – character verification + validator smoke tests
551 GT validator OK
py_compile OK
zip integrity OK
```

### Commit

```bash
git add .
git commit -m "feat(data-guard): add 551 gold fidelity blockers"
git tag -a v0.9.5.96 -m "v0.9.5.96 551 Gold Fidelity Gate"
```
