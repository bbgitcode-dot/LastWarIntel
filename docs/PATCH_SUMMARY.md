# Patch Summary – v0.9.5.98

## Sentinel v0.9.5.98 – Auto Character Re-OCR Activation

### Why this patch exists
The v0.9.5.97 run exposed the right blocker: `character_verification_candidate_rows = 41`, but `character_reocr_target_count = 0` in the normal command path. That meant the evidence layer existed but was not activated unless the exact optional flags were supplied.

### What changed
- Character re-OCR is now auto-enabled by default when screenshots can be found.
- The validator can read screenshots from a directory or directly from a ZIP such as `551.zip`.
- `--no-verify-characters` disables the behavior explicitly.
- If the OCR provider is missing, Sentinel still records unresolved target evidence instead of silently emitting zero targets.
- Added regression coverage for ZIP discovery and target emission without a provider.

### Expected result
Running the same validator command should now produce non-zero `character_reocr_target_count` when `551.zip` or a screenshot directory is available.

### Version
`0.9.5.98`
