## v0.9.5.90 Lesson – Visible Rank Is Structure, Not a Hint

Power sorting is useful only when no visible rank evidence exists. Once OCR or review evidence sees a rank slot, that slot is part of Operational Truth structure and must not be rewritten by recovery.

## v0.9.5.90 Lesson – Candidates Are Evidence, Not Truth

A recovery candidate can be highly plausible and still be unsafe. Ambiguous high-explosion and low-truncation cases must expose candidates to review without silently replacing the observed value or identity.

## v0.9.5.90 Lesson – Exports Are Review Surfaces Too

It is not enough for the internal pipeline to preserve `pending_review`, `rank_slot_preserved` and raw observed identity. If Excel exports omit those fields, alliance leadership or reviewers may see a clean-looking rank list while the system actually held uncertainty. Every human-facing surface must show pending rank slots and observed identity before normalized/canonical identity.

## v0.9.5.90 Lesson – Full Smoke Must Be Trustworthy

Targeted smoke tests are useful for sprint validation, but v1 needs a full smoke command that can be trusted. Legacy files that are shell commands or import stale config symbols create noise and hide real failures. Cleaning the smoke collection is now a data-quality priority, not housekeeping.

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


## v0.9.5.87 Lesson – Cache Is Not Truth

OCR cache is a performance optimization, not an authority. During recognition and ranking-integrity work, cached OCR can preserve old defects and invalidate benchmark conclusions. Development mode must recompute evidence until data quality is stable.

## v0.9.5.88 Lesson – Handoff Is a Product Feature

Sentinel has become large enough that documentation is no longer a side artifact. A clean handoff is part of delivery quality. Each new chat must know the current baseline ZIP, the role model, the no-snippets release rule, the Data Quality priority, and the exact next validation task.

## v0.9.5.88 Lesson – Performance Cannot Validate Truth

The OCR cache can make repeat runs dramatically faster, but fast runs are not proof of better recognition. During data-quality work, speed optimizations must be disabled or version-gated so stale evidence cannot mask defects.

## v0.9.5.88 Lesson – Rank Slots Are Operational Structure

A rank is not only a display number. It is the structural position of an observed row. Quarantine must preserve the slot. Removing a bad row and renumbering later rows creates false Operational Truth.
