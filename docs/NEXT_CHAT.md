# NEXT CHAT – Sentinel v0.9.5.81 Handover

Baseline: **Sentinel v0.9.5.81 – Review Evidence Model**

Use `Sentinel_v0.9.5.81.zip` as the next baseline.

## Key point

Review evidence is now separated into three concepts:

1. OCR Source – what the screenshot/OCR row says.
2. Operational Mapping – Sentinel's hypothesis and candidate scoring.
3. Operational Truth – only after human resolution / guarded promotion.

Do not display source-row ordinals as proven ranks. Keep the yellow overlay, but label it as OCR Row when global rank is not proven.

## Next likely work

Return to recognition quality: false power explosions, ambiguous candidate margins, review-history cleanup, and runtime profiling.
