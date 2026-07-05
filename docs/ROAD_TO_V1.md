# Road to V1 – Sentinel v0.9.5.101

## Strategic sequence

1. Stabilize 551 as a Gold Fidelity benchmark.
2. Expand screenshot-fidelity validation to more servers only after 551 is trusted.
3. Build reliable full-scope acquisition across 549–676.
4. Only then build player/entity intelligence for joiners, leavers, growth and decline.

## Current milestone

v0.9.5.101 continues the Gold Fidelity phase. v0.9.5.100 fixed false character-drift caused by alignment gaps. v0.9.5.101 improves the next bottleneck: crop precision and conservative vote selection for true character targets.

## Not yet V1-ready

Sentinel is not ready for reliable long-term joiner/leaver intelligence until names and alliance tags can be read screenshot-faithfully or explicitly marked unresolved.

## Next milestone candidate

After validating v0.9.5.101, choose between:

- Field-level name/tag segmentation if crops still include neighbouring UI; or
- Language/profile-specific ReOCR retries if crops are clean but OCR cannot read the glyphs.
