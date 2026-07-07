## v0.9.5.117 – Reconstruction Candidate Gate

- Gates expensive Latin Name Block Reconstruction to residual high-confidence Latin-only player-name blockers.
- Skips block reconstruction when cheaper glyph ReOCR already verified all local player-name targets.
- Keeps DATAGUARD conservative: no UNKNOWN, mixed CJK/Hangul/Kana, nonlocal target, weak alignment, power-mismatch, or alliance-mismatch expansion.
- Preserves v0.9.5.116 quality path while reducing unnecessary OCR work on already-solved names such as Joncollins21 and Tragedy122280.

## v0.9.5.112 – Verified Display Evidence Apply Hotfix

v0.9.5.111 introduced verified-display fields, but the validator counted evidence through a legacy `item.target.field` lookup. The active `CharacterVerificationEvidence` stores the field directly as `item.field`, so rows such as `Joncollinszl`/`PBC` still showed raw OCR values in `verified_name_display` and `verified_alliance_display` even though all local glyphs were `verified_expected`.

### Fixed

- Count Character ReOCR evidence from the direct `field` attribute.
- Apply fully verified local glyph evidence into `verified_name_display` and `verified_alliance_display`.
- Preserve the conservative block for skipped/nonlocal glyph drift; CJK/Hangul display drift is still not silently promoted.

### Validation

```text
pytest tests/smoke/test_verified_display_112.py tests/smoke/test_glyph_verification_109.py tests/smoke/test_alliance_tag_glyph_110.py
py_compile OK for changed validator module
zip integrity OK
```

### Commit

```bash
git add .
git commit -m "fix(data-guard): count verified display evidence from direct fields"
git tag -a v0.9.5.112 -m "v0.9.5.112 Verified Display Evidence Apply Hotfix"
```

## v0.9.5.111 – Verified Display Resolution

v0.9.5.110 proved the missing piece for `[PbC]`/`PBC`: the full-tag-block anchor can verify the expected case-sensitive tag from the current screenshot. v0.9.5.111 turns those ReOCR proofs into validator-visible resolved display identity instead of leaving them only in debug evidence.

### Changed
- Added verified-display fields for player name and alliance tag (`verified_name_display`, `verified_alliance_display`).
- Added verified exact identity metrics that count rows where OCR display drift is fully resolved by Character ReOCR evidence.
- Gold-Fidelity blockers now use verified display identity, not only raw OCR display identity.
- Kept conservative behavior: skipped/nonlocal glyph drift cannot become gold automatically.
- Added smoke coverage for the verified-display resolution gate.

### Why it matters
Joncollins-style first-contact rows no longer stop at “debug says the expected glyphs were seen.” If all local drift targets are verified, the validator can now treat `Joncollinszl / PBC` as screenshot-proven `Joncollins21 / PbC` for fidelity scoring without depending on historical player memory.

### Commit / Tag
```bash
git add .
git commit -m "feat(data-guard): apply verified display resolution to gold fidelity"
git tag -a v0.9.5.111 -m "v0.9.5.111 Verified Display Resolution"
```

## v0.9.5.110 – Alliance Tag Glyph Block Anchor

v0.9.5.109 reduced unnecessary Character ReOCR from broad/nonlocal drift and proved that player-name glyphs such as `Joncollins21` can be verified screenshot-locally. The remaining blocker is alliance-tag fidelity, especially case-sensitive tags such as `PbC` being exported as `PBC`. v0.9.5.110 changes tag verification from single-glyph-first to full-tag-block-first. Sentinel now tries to read the complete short tag block (`[TAG]` / `TAG`) before falling back to individual glyph probes.

### Implemented

- Added full alliance-tag block anchor candidates before noisy single-glyph tag crops.
- Preserved screenshot-local verification: no historical player database and no manual identity lookup.
- Improved `[PbC]`/`PBC` case-sensitive verification by selecting the target glyph from the complete tag block when available.
- Kept the v0.9.5.109 local-glyph gate and `character_reocr_skipped_nonlocal` behavior unchanged.
- Added regression tests for tag-block candidate ordering and `[PbC]` case verification.

### Validation

```bash
pytest -q tests/smoke/test_alliance_tag_glyph_110.py tests/smoke/test_glyph_verification_109.py tests/smoke/test_targeted_character_reocr_geometry_106.py tests/smoke/test_character_reocr_103.py
python -m py_compile ground_truth_validator.py parser/targeted_character_reocr.py
```

### Commit

```bash
git add .
git commit -m "fix(data-guard): anchor alliance tag glyph verification on full tag blocks"
git tag -a v0.9.5.110 -m "v0.9.5.110 Alliance Tag Glyph Block Anchor"
```

## v0.9.5.109 – Glyph Verification Engine Gate

v0.9.5.108 proved that telemetry works and showed the next architectural issue: Character ReOCR was spending large CPU time on broad display drift that local glyph verification cannot safely solve. v0.9.5.109 changes the validator from “re-read every visible difference” to “re-read only true local glyph ambiguities”. This keeps the solution independent of historical player databases and focused on the current screenshot.

### Changed
- Added a local glyph target filter before Character ReOCR.
- Keeps high-value confusable cases such as `Joncollinszl` → `Joncollins21` (`z/2`, `l/1`) and case-sensitive alliance tags such as `PbC` → `PBC`.
- Skips non-local broad drift such as Hangul/CJK replacement spans, UNKNOWN-expanded names, and insertion/deletion tails that cannot be proven by a single glyph crop.
- Adds `character_reocr_skipped_nonlocal` to validation summary, category summary, failure summary, and JSON reports.
- Keeps DataGuard conservative: skipped non-local drift remains a Gold Fidelity blocker; it is not auto-corrected and not silently accepted as exact identity.

### Intent
Sentinel must not depend on historical identity memory to read first-contact screenshots from the 549–676 transfer bucket or the broader 2000+ server universe. The path to V1 is therefore local proof: correct row, correct field, correct glyph. v0.9.5.109 narrows the expensive glyph verifier to the subset where that local proof is realistic.

### Validation
```text
pytest -q tests/smoke/test_glyph_verification_109.py tests/smoke/test_targeted_character_reocr_geometry_106.py tests/smoke/test_character_reocr_debug_102.py
python -m py_compile ground_truth_validator.py parser/targeted_character_reocr.py
zip integrity OK
```

### Commit
```bash
git add .
git commit -m "feat(data-guard): gate reocr to local glyph verification"
git tag -a v0.9.5.109 -m "v0.9.5.109 Glyph Verification Engine Gate"
```

## v0.9.5.108 – Runtime JSON Serialization Hotfix

v0.9.5.107 correctly added runtime telemetry, but the first long CPU-only validator run exposed a report-writing bug: pandas/numpy scalar values such as `int64` could enter `runtime_debug_report.json` through fields like `slowest_target_rank`. The validation itself could complete, but the process crashed while serializing the runtime report.

Changes:
- Adds a JSON-safe conversion layer for runtime telemetry payloads.
- Converts pandas/numpy scalars, tuples, lists, dictionaries, and NaN-like values before writing `runtime_debug_report.json`.
- Keeps runtime telemetry observational only; it does not change matching, inference, ReOCR voting, or Operational Truth.
- Preserves the `.107` alliance-tag and timing instrumentation behavior.

Validation:
```text
py_compile OK
runtime payload JSON serialization smoke OK
zip integrity OK
```

Commit:
```bash
git add .
git commit -m "fix(data-guard): serialize runtime telemetry safely"
git tag -a v0.9.5.108 -m "v0.9.5.108 Runtime Telemetry Serialization Hotfix"
```

## v0.9.5.107 – Alliance Tag Fidelity + Runtime Telemetry

v0.9.5.106 finally proved that calibrated Character ReOCR can recover the Joncollins tail digits (`2` and `1`) from screenshot evidence, but alliance-tag case fidelity remains a blocker (`PbC` still often appears as `PBC`). v0.9.5.107 keeps the conservative DataGuard posture and adds two focused improvements.

### Changed
- Added wider full-tag ReOCR candidates for alliance tags so short tags such as `[PbC]` can be read as a field before selecting the target character.
- Added per-target timing fields to Character ReOCR evidence: `target_total_ms`, `crop_generation_ms`, `variant_build_ms`, `ocr_read_ms`, and `vote_selection_ms`.
- Added `benchmarks/runtime_debug_report.json` and `benchmarks/runtime_debug_report.xlsx` to show where long Validator/ReOCR runs spend their time.
- Extended Character ReOCR debug output with the new timing columns.

### DataGuard posture
- Runtime telemetry is observational only. It does not change matching, inference, ReOCR votes, or Operational Truth.
- Gold Fidelity remains blocked unless player name, alliance tag, rank, and power are exact or character-verified.

### Commit
```bash
git add .
git commit -m "feat(data-guard): add runtime telemetry and tag crop calibration"
git tag -a v0.9.5.107 -m "v0.9.5.107 Alliance Tag Fidelity and Runtime Telemetry"
```

## v0.9.5.106 – Character Crop Calibration Harness

v0.9.5.105 proved that fixed mini-crops were too brittle: Joncollins21/PbC targets were detected correctly, but the title-line crops often produced `crop_no_text_detected` or non-target CJK noise. v0.9.5.106 keeps the DataGuard rules conservative and adds a deterministic crop-calibration harness around every targeted Character ReOCR crop.

### Changed
- Added calibrated crop candidates around the primary character crop (`base`, `left_wide`, `right_wide`, `up_wide`, and combined variants).
- Moved visible-window title-line crops slightly upward so orange commander-name glyphs are not clipped at the top.
- ReOCR now ranks candidate crops by verified expected/observed status, crop diagnostics, non-empty votes, and confidence.
- Added debug fields: `crop_candidate_index`, `crop_candidate_count`, and `crop_candidate_reason`.
- Added smoke coverage proving an empty base crop can be recovered by a calibrated fallback candidate.

### Guardrails
- ReOCR still does not modify Operational Truth.
- Expected-character verification remains required for Gold Fidelity; observed/noise votes do not auto-correct identity.
- Alignment context gaps still bypass Character ReOCR.

### Commit
```bash
git add .
git commit -m "fix(data-guard): add calibrated character crop fallback"
git tag -a v0.9.5.106 -m "v0.9.5.106 Character Crop Calibration Harness"
```

## v0.9.5.105 – Character Crop Line Focus Guard

v0.9.5.105 targets the concrete Joncollins21/PbC failure exposed by the v0.9.5.104 reports. The pipeline already detected the right row and the right high-value character targets, but the character crops still included the wrong pixels: late player-name crops hit the final/empty area or non-name text, while alliance-tag crops included neighbouring glyphs and the lower `Warzone #551` line.

### Changed

- Added a Latin-name glyph-pitch crop model for visible-window screenshots.
- Kept Joncollins-style tail-character crops on the title line and centered on the actual `2`/`1` glyphs.
- Reduced visible-window alliance-tag crops to the target glyph instead of the full tag neighborhood.
- Shortened visible-window character crops vertically to avoid the lower `Warzone #551` line.
- Added v0.9.5.105 smoke coverage for Joncollins tail digits and `[PbC]` middle-glyph crops.

### Expected validation movement

- Fewer `crop_no_text_detected` cases for late Latin-name characters.
- Fewer `crop_power_column_bleed` false diagnostics on title-line tail digits.
- Better chance that `Joncollins21 -> Joncollinszl` resolves expected `2/1` instead of staying unresolved.
- Better chance that `PbC -> PBC` verifies the case-sensitive middle `b`.

### Commit

```bash
git add .
git commit -m "fix(data-guard): focus character crops on title-line glyphs"
git tag -a v0.9.5.105 -m "v0.9.5.105 Character Crop Line Focus Guard"
```

## v0.9.5.104 – Character Geometry & Tag Fidelity Guard

v0.9.5.104 focuses on the blocker exposed by the v0.9.5.103 debug run: Character ReOCR was active, but late player-name crops could still leak into the power column and alliance-tag crops for `[PbC]`/`PBC` were too wide and too far to the right.

### Changed
- Tightened visible-window player-name crop geometry so late-name targets such as `Joncollins21` positions `2/1` stay inside the identity column instead of reading power digits.
- Tightened visible-window alliance-tag glyph crops so middle-tag case checks such as `PbC` vs `PBC` inspect the target glyph instead of the `C]`/right-bracket area.
- Added `crop_power_column_bleed` diagnostics when player-name ReOCR votes are dominated by power-like digits.
- Kept Character ReOCR evidence-only; no Operational Truth is changed from ReOCR.

### Validation
```text
9 passed – Ground Truth Validator + Character Geometry smoke tests
py_compile OK
zip integrity OK
```

### Commit
```bash
git add .
git commit -m "fix(data-guard): tighten character geometry and tag fidelity diagnostics"
git tag -a v0.9.5.104 -m "v0.9.5.104 Character Geometry and Tag Fidelity Guard"
```

## v0.9.5.103 – ReOCR Row Slot & Field Anchor Correction

v0.9.5.103 addresses the main finding from the v0.9.5.102 debug reports: Character ReOCR was often looking at the wrong vertical row or at a crop without the expected field anchor. This was visible when `[PbC]` targets sometimes read `[IVE]`, proving that the blocker was crop localization rather than raw OCR strength.

### Changed

- Added window-screenshot row geometry for 551-style screenshots around 627x915 instead of forcing the older 600x1064 normalized row pitch.
- Character ReOCR now records crop-anchor diagnostics: `crop_anchor_status`, `crop_anchor_text` and `crop_diagnostic`.
- The debug report can now distinguish `crop_field_mismatch`, `crop_no_text_detected` and `vote_outside_allowed_set` instead of only `no_votes` / `no_selected_char`.
- Alliance-tag and player-name crops remain evidence-only. No automatic identity correction is performed.

### Guardrails

- Operational Truth is unchanged.
- Alignment context gaps remain excluded from Character Verification.
- Cache behavior is untouched and remains unsuitable for data-quality validation unless explicitly requested.

### Validation

```bash
pytest -q tests/smoke/test_character_reocr_103.py tests/smoke/test_targeted_character_reocr_97.py tests/smoke/test_character_reocr_debug_102.py
python -m py_compile ground_truth_validator.py parser/targeted_character_reocr.py
```

### Commit

```bash
git add .
git commit -m "fix(data-guard): correct reocr row geometry and crop diagnostics"
git tag -a v0.9.5.103 -m "v0.9.5.103 ReOCR Row Slot and Field Anchor Correction"
```

## v0.9.5.102 – Character ReOCR Debug Instrumentation

v0.9.5.102 adds diagnostic instrumentation for the 551 Gold Fidelity sprint. After v0.9.5.101 failed to materially improve Character ReOCR validation, this patch stops guessing at crop fixes and makes the ReOCR path inspectable target by target.

### Added

- `character_reocr_debug_report.json` and `character_reocr_debug_report.xlsx` from the Ground Truth Validator.
- Flattened Character ReOCR debug rows with screenshot, row slot, crop box, crop strategy, vote variants, raw vote texts, selected glyph, confidence and final status.
- Diagnostic metadata in `CharacterVerificationEvidence`: `crop_strategy`, `text_length`, `expected_text`, `observed_text` and `allowed_chars`.
- Smoke tests for the new debug report generation.

### Guardrails

- Operational Truth is not changed.
- Character ReOCR still remains evidence-only.
- Alignment context gaps remain excluded from Character Verification.
- Cache behavior is untouched.

### Validation

```bash
pytest -q tests/smoke/test_character_reocr_debug_102.py tests/smoke/test_targeted_character_reocr_97.py tests/smoke/test_character_reocr_98.py tests/smoke/test_alignment_guard_100.py
python -m py_compile ground_truth_validator.py parser/targeted_character_reocr.py
```

### Commit

```bash
git add .
git commit -m "feat(data-guard): instrument character re-ocr debug evidence"
git tag -a v0.9.5.102 -m "v0.9.5.102 Character ReOCR Debug Instrumentation"
```

## v0.9.5.101 – Character Crop Precision Guard

v0.9.5.101 tightens targeted Character Re-OCR after v0.9.5.100 proved the Alignment Guard was working but only 2 of 8 expected glyph confirmations were observed. The main cause was crop and vote pollution: player-name crops still included alliance tags, and alliance-tag votes could select bracket/neighbor characters instead of the requested tag glyph.

### Changed

- Player-name character crops now start after the bracketed alliance tag instead of at the beginning of the identity column.
- Alliance-tag vote extraction is position-aware inside bracketed tags such as `[PbC]`.
- ReOCR votes are now conservative: only expected, observed, or explicit confusion-family characters can be selected as evidence. Off-target OCR noise becomes `unresolved`, not `ambiguous_vote`.
- Added regression tests for `[PbC]`/`[PBC]` tag position voting and off-target noise suppression.
- Updated documentation and version metadata to v0.9.5.101.

### Validation

```bash
pytest -q tests/smoke/test_targeted_character_reocr_97.py tests/smoke/test_character_reocr_98.py tests/smoke/test_alignment_guard_100.py
python -m py_compile ground_truth_validator.py parser/targeted_character_reocr.py
```

### Commit

```bash
git add .
git commit -m "fix(data-guard): tighten character re-ocr crop and vote precision"
git tag -a v0.9.5.101 -m "v0.9.5.101 Character Crop Precision Guard"
```

## v0.9.5.100 – Ground Truth Alignment Guard

v0.9.5.100 separates contextual alignment gaps from true character-fidelity drift. The previous validator path could compare a Ground Truth row against a neighbouring OCR row accepted only as read-only contextual inference, producing false character differences such as `K9 Thunder` versus `YUNS` or `HUNI` versus `Zacharys`.

### Changed

- Added an Alignment Guard after contextual inference.
- Contextual inference rows now receive `alignment_guard_status = context_gap_no_character_verification`.
- Character Verification and Character ReOCR are suppressed for `inference_context_gap` rows.
- Alignment context gaps no longer contribute to `gold_fidelity_blocker_rows` or `identity_risk_rows`.
- Reports now include `alignment_guard_summary` and `alignment_context_gaps` sections/sheets.
- Updated documentation and version metadata to v0.9.5.100.

### Validation

```bash
pytest -q tests/smoke/test_alignment_guard_100.py
python -m py_compile ground_truth_validator.py inference/context_engine.py parser/targeted_character_reocr.py
```

### Commit

```bash
git add .
git commit -m "fix(data-guard): separate alignment gaps from character verification"
git tag -a v0.9.5.100 -m "v0.9.5.100 Ground Truth Alignment Guard"
```

## v0.9.5.99 – Character Re-OCR Provider Input Fix

v0.9.5.99 fixes the runtime blocker found in v0.9.5.98 where targeted character re-OCR passed PIL image crops directly into EasyOCR. EasyOCR expects a file path, bytes or numpy array, so the validator crashed with `ValueError: Invalid input type`.

### Changed
- Convert PIL crop variants to RGB numpy arrays before calling Sentinel's EasyOCR provider.
- Keep fallback behavior conservative: if no OCR provider is available, evidence can still be emitted as unresolved rather than modifying Operational Truth.
- Version and documentation updated to v0.9.5.99.

### Validation
- `python -m py_compile ground_truth_validator.py parser/targeted_character_reocr.py`
- Targeted unit smoke with fake reader confirms PIL crops are converted and evidence is produced.
- ZIP integrity check.

### Commit
```bash
git add .
git commit -m "fix(data-guard): convert character re-ocr crops for EasyOCR"
git tag -a v0.9.5.99 -m "v0.9.5.99 Character Re-OCR Provider Input Fix"
```

## v0.9.5.99 – Character Re-OCR Provider Input Fix

v0.9.5.99 fixes the v0.9.5.97 validation gap where Character Verification candidates were counted but no targeted re-OCR targets were emitted in the standard validator run.

### Added
- Ground Truth validator now auto-discovers screenshot evidence by default.
- `--screenshots-dir` accepts both directories and ZIP files such as `551.zip`.
- Added `--no-verify-characters` for explicit opt-out.
- Character re-OCR evidence is emitted even when the OCR provider is unavailable; targets are then marked unresolved instead of silently staying at zero.
- Added regression tests proving ZIP discovery and non-zero target emission for `Joncollins21` / `Joncollinszl` and `PbC` / `PBC`.

### Validation
- 5 passed – targeted character re-OCR and ZIP discovery smoke tests.
- 551 validator smoke run against uploaded `lastwar_export.xlsx` and `551.zip` produced `character_reocr_target_count = 183` instead of 0.
- `py_compile` OK.

### Commands
```bash
git add .
git commit -m "fix(data-guard): activate character re-ocr evidence by default"
git tag -a v0.9.5.99 -m "v0.9.5.99 Character Re-OCR Provider Input Fix"
```

## v0.9.5.97 – Targeted Character Re-OCR Evidence

v0.9.5.97 turns the v0.9.5.96 Gold Fidelity blocker list into an actionable screenshot-evidence workflow. It does **not** claim Server 551 is Gold-ready yet. It adds the first conservative implementation of real targeted character re-OCR for player names and alliance tags.

### Added

- `parser/targeted_character_reocr.py`
  - Parses `character_verification_targets` generated by the Identity / Gold Fidelity validator.
  - Locates an approximate row and field crop in the original screenshot.
  - Runs multiple image variants over the crop when an OCR reader is provided.
  - Records per-character votes, selected character, confidence and status.
- `ground_truth_validator.py --verify-characters`
  - Optional mode for targeted screenshot re-OCR evidence.
  - Adds report columns:
    - `character_reocr_status`
    - `character_reocr_targets`
    - `character_reocr_verified_expected`
    - `character_reocr_verified_observed`
    - `character_reocr_unresolved`
    - `character_reocr_evidence`
    - `ground_truth_row_slot`
- Smoke tests for the targeted character re-OCR layer.

### Guardrails

- No fuzzy identity promotion.
- No automatic canonicalization such as `Joncollinszl -> Joncollins21` from context.
- No cache enablement.
- Operational Truth remains unchanged unless screenshot evidence is explicitly verified by future gates.
- Alliance tags remain case-sensitive: `PbC != PBC`, `DAY != daY`.

### How to run the new validator mode

Normal import remains unchanged:

```bash
python main.py --no-ocr-cache
```

Then run the Ground Truth validator normally:

```bash
python ground_truth_validator.py --ocr-output output\snapshots\<snapshot>\lastwar_export.xlsx
```

Optional targeted character re-OCR evidence mode:

```bash
python ground_truth_validator.py --ocr-output output\snapshots\<snapshot>\lastwar_export.xlsx --verify-characters --screenshots-dir screenshots
```

### Validation

```text
9 passed – targeted character re-OCR / character verification smoke tests
551 GT validator smoke run OK
py_compile OK
zip integrity OK
```

### Commit

```bash
git add .
git commit -m "feat(data-guard): add targeted character re-ocr evidence"
git tag -a v0.9.5.97 -m "v0.9.5.97 Targeted Character Re-OCR Evidence"
```

## v0.9.5.113 - Gold Blocker Triage

- Adds a diagnostic Gold Blocker Triage report to the Ground Truth Validator.
- Classifies remaining Gold Fidelity blockers by domain: player name, alliance tag, combined identity, rank/power, alignment, and nonlocal/multilingual drift.
- Adds `gold_blocker_triage_summary` and `gold_blocker_triage` to JSON output plus Excel sheets `gold_blocker_triage` and `gold_blocker_details`.
- Keeps matching, inference, Character ReOCR voting, DataGuard, and Operational Truth unchanged. This sprint is diagnostic, not corrective.


## v0.9.5.115 - Latin Player Name Core Resolution

- Extends the local glyph gate to handle Latin-only missing glyphs in otherwise aligned names.
- Adds safe handling for Latin spacing gaps so formatting does not block Core Identity when the compact Latin name is still locally aligned.
- Keeps mixed CJK/Hangul/Kana display drift conservative; no historical identity database or manual mapping is introduced.
- Adds smoke tests for `Mizzenmast -> Mzzenmast`, Latin spacing gaps, and mixed Unicode rejection.

## v0.9.5.114 - Player Name Drift Triage and Core Identity Gold Gate

- Added a transfer-critical Core Identity gate alongside the stricter full row Gold Fidelity gate. Core Identity means verified player display + verified alliance display + matched power/server; rank display drift is now visible as a separate full-fidelity blocker instead of being mixed with name/tag identity failures.
- Added `verified_core_identity_match`, `verified_core_identity_resolution`, `gold_core_blocker`, `verified_core_identity_matches`, `gold_core_blocker_rows`, and `gold_core_ready` to validator/detail summaries.
- Added `core_identity_summary` and `core_identity_verified_rows` to the JSON report, plus `core_identity` and `core_identity_rows` sheets in the Excel report.
- Improved Gold Blocker Triage classes to separate `identity_core_verified_rank_only_blocker`, `identity_core_verified_power_display_blocker`, multilingual/nonlocal player-name drift, and true local glyph failures.
- No Operational Truth write path changed. DataGuard, row-alignment guard, inference read-only handling, and ReOCR voting remain conservative.

Expected effect: `.114` will not magically solve CJK/Hangul player-name drift, but it will stop rank-only/full-row fidelity noise from hiding rows where transfer-critical identity is already proven.

## v0.9.5.116 – Latin Name Block Reconstruction

- Added screenshot-local Latin Name Block Reconstruction for aligned Latin-only player names where single-glyph ReOCR is too weak, e.g. missing/shifted characters such as `Mizzenmast -> Mzzenmast`, `Drpeek -> Ieek`, and spacing/digit drifts like `N E R D -> NER0`.
- Reconstruction is DATAGUARD-gated: it only runs on accepted/aligned rows, does not use historical identity data, and refuses mixed CJK/Hangul/Kana display drift.
- Added reconstruction evidence to the existing character ReOCR debug stream with crop strategy `latin_name_block`, candidate text, selected reconstruction, confidence, and timing.
- Core Identity can now accept a verified Latin name block when the whole-name OCR candidate supports the expected display more strongly than the observed OCR string.
