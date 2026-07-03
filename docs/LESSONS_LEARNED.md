## v0.9.5.86 Lesson – Review Identity Must Follow Observed Evidence

A quarantined row ordinal is not enough to identify the human review target. If the same screenshot contains a trusted observed row matching the quarantined identity, the review must anchor to that observed row. Review UI may normalize internally for matching, but must display the observed spelling and alliance tag when available.

This protects the reviewer from validating the wrong player/alliance even when the power candidates are useful.

## v0.9.5.85 Lesson – Cache Observations, Not Truth

OCR is an expensive observation step, especially during repeated benchmark runs over the same screenshots. Caching OCR output is safe only when the cache key is based on screenshot content, OCR provider fingerprint, OCR mode and normalization parameters. The cache must never become evidence about server identity, upload order or ranking position.

## v0.9.5.84 – Power Recovery Diagnostics

The 99-screenshot batch showed that `ambiguous` is not a useful single bucket. A 79B alliance explosion, a 7xxM THP explosion and a 23M low truncation require different tuning strategies. Sentinel now classifies each power-recovery trace by family and tracks near-miss ambiguous cases separately. Future recognition tuning should target one family at a time and measure whether false Operational Truth remains at zero.

# Lessons Learned

## v0.9.5.76

A Review ID or quarantine row index is not a ranking rank. Human review text must reference the visible rank from the screenshot, otherwise the reviewer is sent to the wrong visual row.

Design rule added:

> Review surfaces must separate `review_id`, `raw_review_rank`, `visible_rank`, and `screenshot_rank_window`.

This follows Sentinel's core principle: Data Quality before Intelligence, and quarantine before false Operational Truth.

## v0.9.5.77 Note – Review Context

Review surfaces now separate human-visible rank from internal matching rank. Reviewers should see the screenshot-visible rank, screenshot window and target identity instead of quarantine ordinals. This protects human review quality and prevents misleading validation prompts.
## v0.9.5.80 – Continuous Collection Decision

Screenshot import runs are not collection boundaries. A snapshot may remain `COLLECTING` while open reviews exist, because real Sentinel users can upload screenshots continuously. Transition to `REVIEWING` must be explicit. Source-row-only review evidence must never be rendered as a proven visible/global rank.



## v0.9.5.81 – Review Evidence Model

Reviews now distinguish OCR Source, Operational Mapping, and Operational Truth. Source-row overlays remain useful, but must be labelled as OCR evidence rather than proven ranking facts when global rank mapping is unresolved.


## v0.9.5.82 – Recognition Quality Telemetry

Recognition optimization must be measured before it is tuned. Runtime, recovery rate, ambiguous power reviews and quarantine counts are now first-class import report metrics. The 99-screenshot run should be used as an integration benchmark, not as the only developer feedback loop.


## v0.9.5.83 Note

The fast report-rebuild feedback loop is now considered mandatory before expensive screenshot benchmarks. `python main.py --rebuild-reports` must work without OCR and without changing snapshot state. This preserves development velocity while recognition quality is hardened.
