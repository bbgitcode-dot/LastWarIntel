# Project Status – Sentinel v0.9.5.102

**Current sprint:** v0.9.5.102 Character ReOCR Debug Instrumentation  
**Owner:** Proud Owner  
**Copilot:** Mimir

## Current strategic position

Sentinel has moved from broad OCR acquisition into 551 Gold Fidelity validation. The core DataGuard direction remains correct:

- Quarantine over false Operational Truth.
- Screenshot truth over filename/upload-order assumptions.
- Alignment gaps must not be treated as character drift.
- Cache remains a performance tool only and is not part of data-quality validation.

## Latest known 551 validation state

The latest validator run before this patch showed:

```text
ground_truth_rows = 50
ocr_rows = 101
matched_rows = 50
missing_rows = 0
bad_matches = 0
character_reocr_target_count = 183
character_reocr_verified_expected = 18
character_reocr_verified_observed = 11
character_reocr_unresolved = 150
gold_fidelity_ready = False
```

v0.9.5.101 did not materially improve the result. That means the next productive step is not another blind crop-size adjustment, but visibility into the ReOCR path.

## v0.9.5.102 result

v0.9.5.102 adds Character ReOCR instrumentation:

- a dedicated debug JSON report;
- a dedicated debug Excel report;
- crop and vote metadata per target;
- explicit status categories per target.

This sprint is intentionally diagnostic. It does not claim 551 Gold readiness.

## Next decision point

After running the validator, inspect `benchmarks/character_reocr_debug_report.xlsx` and determine which failure class dominates:

1. Wrong row slot.
2. Wrong crop geometry.
3. Correct crop but weak OCR votes.
4. Correct OCR votes but wrong vote selection.
5. CJK/Hangul glyph limitation in EasyOCR.

Only then should v0.9.5.103 apply the next targeted fix.

## v0.9.5.103 Update – ReOCR Row Slot & Field Anchor Correction

The v0.9.5.102 debug reports proved that Character ReOCR failures are mostly localization failures, not raw OCR failures. v0.9.5.103 therefore adds 551-window screenshot row geometry and explicit crop-anchor diagnostics so future runs can separate wrong-row/wrong-field crops from true character-recognition misses. Operational Truth remains unchanged; ReOCR remains evidence-only.

## v0.9.5.104 Update – Character Geometry & Tag Fidelity Guard

The latest 551 validation reports confirmed that matching/recall is stable, but exact identity is still blocked by Character Fidelity: player-name crops can drift into the power column and alliance-tag crops can miss case-sensitive middle glyphs. v0.9.5.104 tightens the visible-window geometry for both fields and adds `crop_power_column_bleed` as an explicit diagnostic.

Expected next validation signal:
- fewer player-name `vote_outside_allowed_set` cases caused by power digits such as `286`, `320`, or `264`;
- fewer alliance-tag `crop_field_mismatch` cases for `PbC` vs `PBC`;
- more useful Character ReOCR evidence without changing Operational Truth.

Gold Fidelity remains intentionally blocked until player name, alliance tag, rank, and power are exact or character-verified from the screenshot.
