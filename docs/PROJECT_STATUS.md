# Project Status – Sentinel v0.9.5.80

**Current version:** v0.9.5.80  
**Focus:** Continuous screenshot collection and conservative review rank display.

## v0.9.5.80 Note

Normal screenshot import runs now keep the active snapshot in `COLLECTING`. The system no longer assumes a batch run means collection is finished. This supports 24/7 screenshot intake while still allowing operators to explicitly move to `REVIEWING` with `--finish-collection` or UI lifecycle controls.

Review rendering now treats `source_row_only` evidence conservatively. If Sentinel only knows the row within a screenshot, it displays `Source Row` and leaves visible rank unresolved instead of claiming a global rank.

# Project Status

**Current version:** v0.9.5.80  

## v0.9.5.80 Note – Review Identity Consistency

Review IDs now continue from persistent Review History and Review surfaces no longer treat screenshot row ordinals as proven visible/global ranks. If Sentinel only knows the row in a screenshot, it shows `Source Row` and keeps the visible rank unresolved until stronger evidence is available.

## v0.9.5.78 Note – Developer Benchmark & Report Rebuild

The 99-screenshot run is now treated as an integration benchmark, not as the default validation path for every UI/reporting change. Sentinel now supports targeted developer runs and report-only rebuilds:

- `python main.py --rebuild-reports` regenerates Command Center, Review Dashboard and Evidence Pack from `data/latest_import_report.json` without OCR.
- `python main.py --screenshots "<filename-or-glob>"` limits OCR to explicit test screenshots for Review Context and recognition debugging.
- `--skip-excel`, `--skip-command-center` and `--limit` reduce iteration time for small quality checks.

These modes are developer conveniences only. They do not alter the rule that screenshot filename/order/upload order must never be treated as truth.

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
