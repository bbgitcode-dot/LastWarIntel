# Sentinel v0.9.4-pre – Patch 10A

## Transfer Baseline Data Quality Gate

This patch protects the S6 pre-transfer baseline from silent OCR identity errors.

## Added

- Robust player identity quality gate for OCR-derived THP rows
- Alliance tag extraction from bracketed tags anywhere in the OCR name text
- Prefix-noise detection before alliance tags
- Unreadable/unsafe player name handling using `UNKNOWN`
- Explicit `VALID` / `REVIEW` parse status
- Parse warnings and corrections on player ranking rows
- Review-oriented Excel export columns for THP rankings
- Smoke test for transfer baseline identity parsing

## Why this matters

Player Mobility, Joiner/Leaver detection, Whale Migration and Server Health all depend on a reliable pre-transfer baseline. Bad OCR names must not silently become trusted player identities.

## Quality Gate Behavior

Examples:

- `[SW3] Bierbaer` -> alliance_tag=`SW3`, player_name=`Bierbaer`, status=`VALID`
- `FKGzzs [Warf] GoldCradle` -> alliance_tag=`Warf`, player_name=`GoldCradle`, status=`REVIEW`
- `[ABC] 张三` -> alliance_tag=`ABC`, player_name=`UNKNOWN`, status=`REVIEW`
- `Bierbaer` -> alliance_tag=`None`, player_name=`Bierbaer`, status=`REVIEW`

## Tests

Passed:

- `tests/smoke/test_ranking_type_fallback.py`
- `tests/smoke/test_player_ranking_parser.py`
- `tests/smoke/test_ocr_normalization.py`
- `tests/smoke/test_transfer_baseline_quality_gate.py`
- `compileall parser models`

## Git

Suggested commit:

`feat(data-quality): add transfer baseline identity quality gate`

Suggested tag after rollout and verification:

`v0.9.4-pre-transfer-baseline`

## Wolf Checklist

🐺 Alliance Tag Extraction hardened
🐺 Unreadable OCR names routed to REVIEW
🐺 UNKNOWN player identity handled explicitly
🐺 Review export columns added
🐺 Regression tests passed
🐺 Patch ZIP created

The Sentinel approves.
