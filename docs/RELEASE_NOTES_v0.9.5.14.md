# Sentinel v0.9.5.14 - Sequence Alignment & Power Recovery

## Goal

Reduce shifted ranking-block errors by treating THP values as recoverable sequence anchors instead of isolated row fields.

## Added

- `parser/power_normalization.py`
  - exact THP comparison
  - near THP comparison
  - truncated digit recovery (`x10`)
  - bounded zero-insertion recovery
  - explainable `PowerMatchResult`

- `parser/sequence_alignment.py`
  - sequence-aware candidate scoring
  - power + name + alliance + rank evidence fusion
  - conservative recovered-power matching
  - protection against recovered-power false positives without name evidence

## Changed

- Ground Truth Validator now prefers sequence-aware matching before rank fallback.
- Validator report now includes:
  - `ocr_power_recovered`
  - `power_exact_match`
  - `power_recovered_match`
  - `power_match_type`
  - `power_similarity`
  - `sequence_alignment_score`

## Measured Impact on Server 551 Ground Truth

- Score: `60.54 -> 62.59`
- Power matches: `33 -> 36`
- Usable identities: `23 -> 26`
- Recovered power matches: `4`

## Notes

This release intentionally keeps recovered power conservative. Recovered THP can only override rank-based fallback when the player name still provides strong supporting evidence.
