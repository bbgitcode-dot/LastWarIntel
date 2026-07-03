# NEXT CHAT – Sentinel v0.9.5.80 Handover

Baseline: **Sentinel v0.9.5.80 – Continuous Collection & Source-Row Review Clarity**

Use `Sentinel_v0.9.5.80.zip` as the next baseline.

## Current Focus

Data recognition and review clarity remain the active priority before expanding Intelligence.

## What changed in .80

- Normal `python main.py` imports no longer move an active snapshot to `REVIEWING` automatically.
- Operators must explicitly finish collection with `python main.py --finish-collection` or through the UI lifecycle.
- Review rendering was hardened for `source_row_only`: a screenshot row is no longer displayed as a proven visible/global rank.

## Next likely sprint

Continue Recognition Quality:

- verify source-row-only Review Detail in fresh rebuilt reports;
- align target identity, highlight row and source row for ambiguous reviews;
- reduce power explosion / ambiguous candidate cases;
- keep the 99-screenshot dataset as an integration benchmark, not a routine test.
