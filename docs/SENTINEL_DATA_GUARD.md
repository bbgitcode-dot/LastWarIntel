# Sentinel Data Guard

**Current version:** v0.9.5.92

## Principle

Data Quality comes before Intelligence. Quarantine is preferred over false Operational Truth.

## v0.9.5.92 Addendum – Rank Evidence vs Final Rank

Sentinel separates rank evidence from final exported truth:

- `visible_rank` / `ocr_rank`: observed OCR evidence from the screenshot.
- `computed_rank`: row position after reconstruction/power order.
- `rank` / `operational_rank` / `final_rank`: export/Operational Truth rank.

For partial windows, screenshot-visible ranks stay authoritative. For full-scope/multi-window imports, Last War's power-sorted ranking context may infer or repair final ranks when OCR rank evidence is missing or broken. The repair must be explainable via `rank_context_status`, `merge_reason`, and `rank_warning`.

## Protected failure families

- Rank Context Corruption
- Window Merge Contamination
- Visible Rank Loss
- Rank Scope Violation
- Identity Drift
- Duplicate Identity
- Power Explosion
- Low-Truncation Power Ambiguity
