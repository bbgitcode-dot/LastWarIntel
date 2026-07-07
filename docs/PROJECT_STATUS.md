## v0.9.5.117 – Reconstruction Candidate Gate

Current focus: reduce validator runtime without weakening DATAGUARD. v0.9.5.116 proved block reconstruction can resolve additional Latin identities, but it ran too broadly. v0.9.5.117 introduces a candidate gate so the expensive block pass is reserved for residual Latin blockers rather than already-resolved glyph cases.

Next validation target: compare character_reocr target_total_ms and verified_core_identity_matches against v0.9.5.116. Desired result is stable core identity count with lower runtime.

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


## v0.9.5.111 Update – Verified Display Resolution

v0.9.5.110 produced the evidence needed to solve the Joncollins/PbC class: player-name tail glyphs and the case-sensitive alliance tag can now be verified from the screenshot. v0.9.5.111 promotes that evidence into explicit verified-display identity fields. Raw OCR remains visible, but fidelity decisions can now use the screenshot-proven display values when every local glyph drift is verified. Nonlocal/CJK drift remains blocked and visible; it is not silently promoted to gold.

Current strategy after .111: run the 551 validation again and measure whether `verified_exact_identity_matches`, `verified_identity_resolution_rows`, and `gold_fidelity_blocker_rows` move as expected. If Joncollins is resolved but many blockers remain, the next sprint should target the remaining unresolved local glyph classes rather than reworking tag geometry again.

## v0.9.5.112 Update – Verified Display Evidence Apply Hotfix

The v0.9.5.111 run proved that the ReOCR evidence existed but was not applied to the final verified-display metrics. v0.9.5.112 fixes the evidence counter so `CharacterVerificationEvidence.field` is counted directly. Rows whose local glyph drift is fully `verified_expected` can now resolve their verified display identity; rows with skipped/nonlocal drift remain blocked.

## v0.9.5.113 - Gold Blocker Triage

- Adds a diagnostic Gold Blocker Triage report to the Ground Truth Validator.
- Classifies remaining Gold Fidelity blockers by domain: player name, alliance tag, combined identity, rank/power, alignment, and nonlocal/multilingual drift.
- Adds `gold_blocker_triage_summary` and `gold_blocker_triage` to JSON output plus Excel sheets `gold_blocker_triage` and `gold_blocker_details`.
- Keeps matching, inference, Character ReOCR voting, DataGuard, and Operational Truth unchanged. This sprint is diagnostic, not corrective.


## v0.9.5.115 - Current Sprint Status

The previous run showed a clean split: alliance-tag verification is largely stable, while player-name display drift remains the main Core Identity blocker. v0.9.5.115 therefore targets Latin-only player names where OCR dropped or compressed a local glyph, such as `Mizzenmast -> Mzzenmast`, without opening the door to broad CJK/Hangul substitutions.

The sprint keeps DATAGUARD conservative: mixed-script display drift is not auto-resolved and still requires future OCR strategy improvements. Core Identity progress must come from screenshot-local evidence, not historical name databases.

## v0.9.5.114 - Current Sprint Status

The previous run showed that alliance-tag verification is no longer the main blocker: verified alliance display exactness is high, while player-name display drift remains the primary source of full Gold Fidelity blockers. v0.9.5.114 therefore introduces a second, explicit gate: Core Identity.

Core Identity is intentionally transfer-focused: server + power + verified player display + verified alliance display. Full Gold Fidelity remains stricter and still includes rank/display fidelity. This separation prevents rank-only drift from being treated as equivalent to a wrong player name.

Next focus remains player-name drift triage: latin-only glyph/separator fixes first, then conservative handling for mixed CJK/Hangul names where local glyph verification is not enough.

## v0.9.5.116 – Latin Name Block Reconstruction

- Added screenshot-local Latin Name Block Reconstruction for aligned Latin-only player names where single-glyph ReOCR is too weak, e.g. missing/shifted characters such as `Mizzenmast -> Mzzenmast`, `Drpeek -> Ieek`, and spacing/digit drifts like `N E R D -> NER0`.
- Reconstruction is DATAGUARD-gated: it only runs on accepted/aligned rows, does not use historical identity data, and refuses mixed CJK/Hangul/Kana display drift.
- Added reconstruction evidence to the existing character ReOCR debug stream with crop strategy `latin_name_block`, candidate text, selected reconstruction, confidence, and timing.
- Core Identity can now accept a verified Latin name block when the whole-name OCR candidate supports the expected display more strongly than the observed OCR string.

## Current Sprint – v0.9.5.120

The current focus is Latin Residual Core Blocker Cleanup. `.118` successfully reduced mixed Latin/CJK/Hangul blockers through a script-limited policy. `.119` now handles the analogous Latin-only residual class: stable Latin core + verified alliance + matched power can satisfy Core Identity when OCR only added prefix/suffix garbage or formatting noise. Broad missing-glyph cases remain blocked and require future OCR/reconstruction work.
