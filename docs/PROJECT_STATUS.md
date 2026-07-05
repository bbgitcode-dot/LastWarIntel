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

## v0.9.5.105 Update – Character Crop Line Focus Guard

The latest Joncollins21 investigation proved that Row Alignment was no longer the blocker: the validator matched the correct row, identified `2/z`, `1/l`, and `PbC/PBC` as exact character targets, and correctly refused to guess. The blocker was the pixel crop. The `2` target was landing on title-line tail/noise, the `1` target was landing on an empty region, and the `b` tag target still included neighbouring tag glyphs plus the lower `Warzone #551` line.

v0.9.5.105 narrows this failure mode by using a visible-window Latin glyph-pitch model, shortening crops to the commander title line, and reducing alliance-tag crops to the target glyph. The sprint keeps DataGuard conservative: unresolved crops remain unresolved and no Operational Truth is modified by ReOCR.

## v0.9.5.106 Update – Character Crop Calibration Harness

The v0.9.5.105 validation run showed a regression: matching and DataGuard remained stable, but targeted Character ReOCR became too narrow. The Joncollins21/PbC case was correctly selected for verification, yet the actual crops returned `crop_no_text_detected` or off-target CJK noise. v0.9.5.106 responds by replacing single fixed mini-crops with a deterministic crop-calibration harness. Each target now tries nearby crop candidates and records which candidate produced the selected evidence.

This sprint is still proof-first: no identity is corrected unless the screenshot crop verifies the expected glyph. Gold Fidelity remains blocked until exact player names and case-sensitive alliance tags can be proven from pixels.



## v0.9.5.108 Update – Runtime Telemetry Serialization Hotfix

The first v0.9.5.107 validator run proved that runtime telemetry is now active, but it also exposed a late report-writing crash: pandas/numpy scalar values from the runtime summary were not JSON-serializable. v0.9.5.108 is a narrow hotfix that makes runtime telemetry JSON-safe without changing matching, inference, ReOCR decisions, or Operational Truth.

## v0.9.5.107 Update – Runtime Telemetry and Tag Fidelity

The latest validation showed strong progress in targeted ReOCR: the Joncollins21 player-name tail digits can now be verified as expected-character evidence. The remaining high-value blocker is alliance-tag display fidelity, especially case-sensitive tags such as `PbC` versus `PBC`. v0.9.5.107 therefore adds full-tag crop candidates and introduces runtime telemetry so long CPU-only runs can be explained by phase and by Character ReOCR target.

New runtime outputs:

- `benchmarks/runtime_debug_report.json`
- `benchmarks/runtime_debug_report.xlsx`

The runtime report separates loading, validation, report writing, OCR reader initialization, and Character ReOCR target timing. This should make the next slow run actionable instead of opaque.


## v0.9.5.109 Update – Glyph Verification Engine Gate

The v0.9.5.108 runtime report showed that long validator runs were dominated by Character ReOCR targets, many of which were not true local glyph problems. v0.9.5.109 adds a gate before ReOCR: only confusable/case-sensitive local glyph targets are reread. Broad display drift remains visible as a blocker but is no longer treated as something a single glyph crop can safely prove.

This keeps the architecture aligned with the transfer-bucket requirement: Sentinel must read first-contact screenshots without relying on a historical player database. The current-screenshot proof path is now: row alignment → field alignment → local glyph verification. If a target is not local, DataGuard keeps it blocked instead of wasting OCR or guessing.

## v0.9.5.110 Update – Alliance Tag Glyph Block Anchor

The v0.9.5.109 run proved that local player-name glyph verification works and sharply reduces unnecessary ReOCR work, but alliance tags remained the dominant identity blocker. In particular, middle tag glyphs such as `b` in `PbC` were often read as `h`, `6`, or CJK-like noise when cropped alone. v0.9.5.110 adds a full-tag-block anchor path so Sentinel first attempts to read the complete short tag before selecting the target glyph. This keeps the first-contact/2000+ server requirement intact: no historical identity memory is required to prove a tag from the current screenshot.

