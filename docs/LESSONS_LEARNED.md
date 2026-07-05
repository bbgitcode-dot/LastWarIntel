# Lessons Learned – Sentinel v0.9.5.102

## Do not tune Character ReOCR blindly

If a crop/vote patch does not move the validation numbers, the next sprint must instrument the pipeline before attempting another fix. v0.9.5.102 adds per-target debug reports for exactly this reason.

## v0.9.5.100 Lesson – Evidence Pipelines Must Be Active by Default

A detector is not enough. v0.9.5.97 correctly identified Character Verification candidates, but the standard validator command left re-OCR target counts at zero. v0.9.5.100 closes that gap: if screenshots are present, target evidence must be emitted automatically, or the system must explicitly say why it cannot verify.

## v0.9.5.97 Lesson – Screenshot Evidence Beats Contextual Guessing

A name must not be canonicalized because context suggests it. If `Joncollinszl` may be a real player, Sentinel must not silently rewrite it to `Joncollins21`. The only acceptable improvement path for Operational Truth is better screenshot evidence.

## v0.9.5.97 Lesson – Targeted Re-OCR Is an Evidence Layer

Targeted character re-OCR should collect votes, crop geometry, selected character and confidence. Until evidence is strong enough, the row remains a Gold blocker.

## v0.9.5.97 Lesson – Alliance Tag Case Is Part of Truth

`PbC` and `PBC` are not display-equivalent for Sentinel. Case-sensitive tags must be preserved or explicitly marked unresolved.
