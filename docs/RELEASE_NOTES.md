
## v0.9.5.95 – Targeted Character Verification Planning

**Purpose**

v0.9.5.95 adds the first deterministic layer for character-level identity fidelity. The sprint does not guess canonical identities. It identifies which visible characters in player names and alliance tags must be re-read from screenshot evidence because they are OCR-confusable or case-sensitive.

**Implemented**

- Added `parser/character_verification.py` with OCR confusion groups for `1/l/I`, `2/z/Z`, `0/O`, `5/S`, `8/B`, `6/G`, and `9/g/q`.
- Added case-sensitive alliance-tag verification targets; `PbC`, `PBC`, `DAY`, and `daY` are treated as different visible identities.
- Extended `ground_truth_validator.py` with character verification candidate metrics and JSON/XLSX sheets:
  - `character_verification_candidate_rows`
  - `high_value_character_verification_rows`
  - `player_name_confusable_drift_rows`
  - `alliance_tag_character_verification_rows`
  - `character_verification_summary`
  - `character_verification_candidates`
- Added tests proving that `Joncollins21` vs `Joncollinszl` creates targeted verification for `2 ↔ z` and `1 ↔ l`.

**Validation**

```bash
pytest -q tests/smoke/test_character_verification_95.py tests/smoke/test_identity_fidelity_validator.py tests/smoke/test_ground_truth_validator.py
python -m py_compile ground_truth_validator.py parser/character_verification.py
zip -T Sentinel_v0.9.5.95.zip
```

**Commit**

```bash
git add .
git commit -m "feat(data-guard): identify targeted character verification candidates"
git tag -a v0.9.5.95 -m "v0.9.5.95 Targeted Character Verification Planning"
```
