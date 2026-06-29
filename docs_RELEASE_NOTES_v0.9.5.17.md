# Sentinel v0.9.5.17 – Gap Resolver

## Focus
Active resolution of recoverable validation gaps caused by screenshot/server bucket leakage.

## Added
- `parser/gap_resolver.py`
- Cross-server gap candidate search for rows exported under the wrong server sheet
- Conservative evidence scoring using power, normalized name, and alliance compatibility
- `gap_resolved_rows` validation metric
- Smoke tests for gap resolver and validator integration

## Improved
- Recoverable gaps are no longer just annotated; high-confidence candidates can now be pulled back into the correct Ground Truth row.
- Wrong rank fallbacks remain blocked unless strong evidence exists.

## Server 551 Benchmark
- Valid matches: 36 → 43
- Bad matches: 13 → 6
- Gap rows: 14 → 7
- Gap resolved rows: 7
- Precision: 0.7500 → 0.8958
- Recall: 0.7200 → 0.8600
- F1: 0.7347 → 0.8775
- Usable identities: 26 → 32
- Score: 53.69 → 63.45
