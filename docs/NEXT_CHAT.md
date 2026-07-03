## Next Chat – After v0.9.5.86

Baseline: `Sentinel_v0.9.5.86.zip`

Recommended validation:

1. Rebuild reports: `python main.py --rebuild-reports`.
2. Inspect Server 553 THP review for Sven: it should anchor to the observed Rank 10 row and prefer raw display identity when available.
3. Run a second identical screenshot import to validate OCR cache hits.
4. Compare runtime and review count against v0.9.5.85.

Likely next sprint: OCR Cache Effectiveness & Data Quality Loop Profiling, unless source-row identity still shows mismatches.

## Next Chat – After v0.9.5.85

Baseline: `Sentinel_v0.9.5.85.zip`

Recommended next step:

1. Run a small smoke test with `python main.py --rebuild-reports`.
2. Run a 1–2 screenshot test twice to verify OCR cache hits on the second run.
3. If stable, run the 99-screenshot benchmark again and compare:
   - Runtime
   - OCR cache hit/miss counts
   - Review items
   - Ambiguous power recoveries
   - Critical count

Likely next sprint: v0.9.5.86 – OCR Cache Extension & Data Quality Loop Profiling.

# NEXT CHAT – Sentinel v0.9.5.84 Handover

Baseline: **Sentinel v0.9.5.84 – Power Recovery Diagnostics & Candidate Family Telemetry**

Use `Sentinel_v0.9.5.84.zip` as the next baseline.

## What changed

- Power recovery traces now include `family`.
- Import reports summarize `by_family`, `ambiguous_by_family` and `near_miss_ambiguous`.
- Recognition Quality exposes the same family counters for Command Center review.
- Command Center power trace tables show the family per trace.

## Recommended next work

Do not run the full 99-screenshot benchmark yet unless a measurable scoring change is expected. First use small targeted runs to inspect:

- alliance high explosions
- THP high explosions
- low truncations
- near-miss ambiguous cases

Next likely sprint: Candidate Scoring Pass focused on one family at a time.
