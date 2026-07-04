# Modus Operandi – Sentinel

**Current release:** v0.9.5.93

## Roles

- Proud Owner: product owner and final strategic authority.
- Mimir: strategic copilot and implementation partner.

## Delivery rule

No snippets as sprint deliverables unless explicitly requested. Every sprint produces a complete downloadable ZIP with version update, documentation, validation summary, `.commit`, commit command and tag command.

## Benchmark rule

The screenshot is the only Ground Truth.

Benchmark review order:

1. Read screenshot.
2. Establish observed truth row by row.
3. Compare Sentinel output to screenshot.
4. Classify every deviation.
5. Only then produce assessment or strategy.

## Cache rule

For data-quality validation, OCR cache is off unless explicitly requested. Cache is a performance tool, not a truth source.

## Rank rule

`visible_rank` / `ocr_rank` are evidence. `rank` / `operational_rank` / `final_rank` are output truth surfaces. In partial forensic windows, visible ranks remain authoritative. In full-scope imports, power-order inference may repair missing or impossible OCR ranks while retaining the raw evidence.

## Identity rule

Identity fidelity is stricter than OCR similarity. Alliance tags are case-sensitive. Player names with digit/letter confusions must be treated as identity-risk evidence, not automatically corrected truth. Fuzzy matching may assist review, but it must never silently rewrite Operational Truth.
