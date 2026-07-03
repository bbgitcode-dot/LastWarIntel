# Lessons Learned

## v0.9.5.76

A Review ID or quarantine row index is not a ranking rank. Human review text must reference the visible rank from the screenshot, otherwise the reviewer is sent to the wrong visual row.

Design rule added:

> Review surfaces must separate `review_id`, `raw_review_rank`, `visible_rank`, and `screenshot_rank_window`.

This follows Sentinel's core principle: Data Quality before Intelligence, and quarantine before false Operational Truth.
