# Patch Summary – v0.9.5.77

## Review Context & Explainability

This patch completes the first Review Context pass after the v0.9.5.76 quality sprint. It fixes the misleading review-rank presentation where an internal quarantine ordinal could appear as the actual ranking rank.

## Changed

- Review evidence now carries target identity context where available:
  - `target_name`
  - `target_alliance`
  - `target_power_original`
  - `target_power_selected`
  - `target_rank` / `raw_review_rank`
  - `visible_rank`
- Review Detail now shows a Review Target card with name/alliance/power.
- Review Queue now surfaces target identity and visible rank.
- Screenshot overlay positioning now uses the row inside the screenshot window, not the global rank number.
- Problem statements now explicitly say `sichtbarer Rang` and include the affected player/alliance when known.

## Validation

```text
11 passed
compileall OK
zip integrity OK
```
