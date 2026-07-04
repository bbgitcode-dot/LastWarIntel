# Handoff Next Chat – Sentinel v0.9.5.94

## Baseline

Use:

```text
Sentinel_v0.9.5.94.zip
```

## Current state

v0.9.5.94 follows the Server 551 v0.9.5.93 validation. Review placeholders no longer leak into normal ranking sheets. The remaining strategic risk is Identity Fidelity: players and alliance tags can match by power/rank but still be unsafe for historical tracking if their visible identity changed.

The Ground Truth validator now reports exact identity metrics and emits an `identity_risks` sheet/JSON section. Use this before any future transfer/player-history work.

## Next recommended sprint

**v0.9.5.95 – Identity Regression / Screenshot Replay**

Purpose:

- Run Server 551 and selected 549-555 screenshots against v0.9.5.94.
- Inspect `identity_risks` line by line against screenshots.
- Decide which OCR identity risks require code fixes versus human alias review.
- Add regression fixtures for `Joncollins21`, case-sensitive tags and high-value top-rank players.

## Operating rule

The screenshot remains the truth. A fuzzy match is not a safe identity.
