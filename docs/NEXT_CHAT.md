# NEXT CHAT

Baseline: **Sentinel v0.9.5.77 – Review Context & Explainability**

Use `Sentinel_v0.9.5.77.zip` as the next baseline.

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

## v0.9.5.77 Note – Review Context

Review surfaces now separate human-visible rank from internal matching rank. Reviewers should see the screenshot-visible rank, screenshot window and target identity instead of quarantine ordinals. This protects human review quality and prevents misleading validation prompts.
