# NEXT CHAT – Sentinel v0.9.5.79 Handover

Baseline: **Sentinel v0.9.5.79 – Review Identity Consistency Fix**

Use `Sentinel_v0.9.5.79.zip` as the next baseline.

## What changed

- Review IDs are persistent and monotonic across runs.
- Source-row-only reviews no longer claim a visible/global rank.
- Review Target, overlay, location and list cards use consistent rank context.

## Recommended next step

Run a small targeted screenshot test first, preferably the two screenshots that reproduced REV-001/REV-002 confusion. Avoid the full 99-screenshot integration run until the Review UI is confirmed.
