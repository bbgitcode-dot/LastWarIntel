# Gold Core Zero II — Promotion Guard Rationalization

## Purpose

Version 0.9.5.146 removes opacity from the Promotion Guard. The former aggregate reason is decomposed into individually testable conditions so every remaining Gold Case shows exactly why promotion was denied.

## Safe override

A blocker may be cleared only when all of the following are true:

- authoritative failure class is `vote_warning_gate_review`;
- legacy block reason is low coverage or evidence budget;
- match is accepted and no context gap exists;
- player name is proven exactly;
- alliance and power are proven;
- warning evidence exists and every selected glyph equals the expected glyph;
- no observed counterevidence exists;
- no unresolved or ambiguous vote exists;
- no crop or field mismatch exists.

## Outputs

The Gold Core elimination report now includes:

- `promotion_guard_checks`
- `promotion_guard_failed_checks`
- `promotion_guard_failed_count`
- `promotion_guard_primary_blocker`
- `promotion_guard_legacy_reason`
- evidence and identity diagnostics

## Invariants

Operational Truth, Ground Truth, snapshots, and OCR exports remain read-only.
