# Patch 10A.4 - Transfer Baseline Integrity Gate

## Purpose

Strengthen the S6 Pre-Transfer import pipeline by preventing silent ranking and server metadata errors.

## Added

- Configurable multilingual OCR foundation.
- Screenshot-level Warzone consensus validation.
- OCR rank extraction from ranking rows.
- Separate `ocr_rank` and `computed_rank` fields.
- Rank integrity warnings for missing or shifted rows.
- Export columns for rank and server quality review.

## Fixed

- Ranking rows are no longer silently renumbered as `n+1` without preserving OCR rank.
- Missing OCR rows can now be detected through rank gaps and rank mismatch warnings.
- Warzone/server detection can now require multiple matching OCR observations before automatic assignment.

## Quality Gates

- A screenshot should only be considered final when Warzone consensus is strong enough or explicitly reviewed.
- Rank gaps are surfaced in the export instead of being hidden by recomputed ranks.
- Player identity quality remains review-first rather than silently accepting weak OCR names.

## Tests

- Multilingual OCR configuration test.
- Ranking integrity validation test.
- Warzone consensus validation test.
- Existing player ranking parser test.
- Existing transfer baseline quality gate test.
- Existing ranking type fallback test.
- Existing OCR normalization test.

## Follow-up

Run a complete reimport of the S6 Pre-Transfer screenshots and inspect:

- `ocr_rank`
- `computed_rank`
- `rank_warning`
- `detected_server`
- `server_confidence`
- `server_warning`
- `server_detections`

Reliable Intelligence begins with reliable data.
