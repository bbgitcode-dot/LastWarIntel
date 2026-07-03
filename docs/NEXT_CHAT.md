# NEXT CHAT

Baseline: **Sentinel v0.9.5.76 – Recognition Quality & Data Integrity Pass**

Use `Sentinel_v0.9.5.76.zip` as the next baseline.

## Important context

- Snapshot workflow is stable enough for now.
- Current priority is screenshot recognition quality, not new Intelligence.
- .76 fixed misleading review ranks by separating visible rank from raw review/quarantine row.
- Review history now distinguishes current-run open reviews from stale historical open reviews.

## Recommended next sprint

**v0.9.5.77 – Candidate Promotion Calibration & Power Explosion Guard**

Goals:

- analyze the remaining ambiguous power candidates from the 99-screenshot run,
- reduce avoidable human reviews without weakening Data Guard,
- improve 77B/79B explosion handling before Ranking Guard,
- preserve explainability for every promoted value.
