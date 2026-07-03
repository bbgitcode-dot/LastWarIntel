# Project Status

**Current version:** v0.9.5.77  
**Sprint:** Recognition Quality & Data Integrity Pass

## Status

Snapshot foundation is functionally closed for now. The active focus has moved back to screenshot-derived data integrity and recognition quality.

## v0.9.5.76 outcome

The first production-style run over 99 screenshots exposed a critical review-reporting issue: review IDs/raw quarantine indices were being presented like visible ranking ranks. This release fixes that by deriving the visible rank from the same screenshot's trusted rank window and preserving the raw review row separately.

Sentinel now reports review location as:

```text
Server
Ranking Type
Visible Rank
Screenshot Window
Raw Review Row
```

instead of collapsing those concepts into a single misleading `rank`.

## Next priority

Continue Recognition Quality hardening:

- reduce ambiguous candidate margins,
- tighten false/aggressive power explosion handling,
- use recognition telemetry to locate runtime bottlenecks,
- keep quarantine preferred over false Operational Truth.

## v0.9.5.77 Note – Review Context

Review surfaces now separate human-visible rank from internal matching rank. Reviewers should see the screenshot-visible rank, screenshot window and target identity instead of quarantine ordinals. This protects human review quality and prevents misleading validation prompts.
