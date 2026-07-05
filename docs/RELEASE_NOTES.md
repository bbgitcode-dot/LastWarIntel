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
