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
