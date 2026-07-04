# Project Status – Sentinel v0.9.5.92

**Current sprint:** v0.9.5.92 Rank Inference & Export Precision Hardening  
**Baseline:** Sentinel v0.9.5.91

Sentinel remains in the Data Quality before Intelligence phase. The isolated Server 551 run after v0.9.5.91 proved a major improvement: the Ground Truth validator matched all 50 gold-standard THP rows with 0 missing rows and 0 bad matches. However, v0.9.5.91 was too conservative at the export boundary: many valid rows were exported with `rank=None`, producing low precision and zero raw rank matches in the validator despite correct identity/power matching.

v0.9.5.92 introduces rank-context inference for full-scope/multi-window imports. Small forensic screenshot slices still keep screenshot-visible ranks authoritative. Larger imports may safely infer final export ranks from power order when OCR rank evidence is missing or obviously broken, while preserving the raw OCR rank as evidence in `visible_rank`/`ocr_rank` and documenting the repair in `rank_warning`.

## Current quality signal

- Server 551 THP gold-standard run after v0.9.5.91: 50/50 matched, 0 missing, 0 bad matches.
- Remaining issue after v0.9.5.91: many correct rows exported with `rank=None`, hurting rank metrics and review ergonomics.
- v0.9.5.92 target: improve rank usability and export precision without reintroducing cross-window rank corruption.

## Current P0 focus

1. Preserve screenshot truth for partial windows.
2. Infer rank from power order only in recognized full-scope or multi-window contexts.
3. Preserve raw rank evidence separately from repaired final rank.
4. Keep ambiguous power values in quarantine.
5. Continue screenshot-first validation; exports are never ground truth.
