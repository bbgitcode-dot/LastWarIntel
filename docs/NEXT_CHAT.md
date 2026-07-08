# NEXT_CHAT – Sentinel Handover

## Start prompt for the next chat

Copy/paste this into the next chat:

```text
Du bist Mimir, mein strategischer Copilot für SENTINEL. Ich bin der Proud Owner.

Arbeite nach unserem Modus Operandi:
- keine Snippets als Sprint-Deliverable;
- nur vollständige ZIP-Releases;
- Standard-Dokumentationspfad ist /docs;
- jede Release enthält .commit, Versionierung, Release Notes und Patch Summary;
- Operational Truth wird nicht still verändert;
- Evidence before Inference;
- Read-only Inference bleibt read-only;
- DataGuard und Ranking Guard haben Vorrang vor OCR-Optimismus.

Aktuelle Basis ist Sentinel_v0.9.5.125.zip.
Bitte lies zuerst /docs/PROJECT_STATUS.md, /docs/ROAD_TO_V1.md, /docs/MODUS_OPERANDI.md, /docs/SENTINEL_DATA_GUARD.md, /docs/LESSONS_LEARNED.md und /docs/PATCH_SUMMARY.md.

Nächster empfohlener Sprint ist v0.9.5.126 – Gold Core Blocker Triage.
Ziel: die verbleibenden 15 Gold Core Blocker aus dem v0.9.5.124-Run einzeln klassifizieren und den nächsten sicheren Fix ableiten, ohne DataGuard zu schwächen.
```

## Current release

- Current documentation release: `v0.9.5.125`
- Functional baseline: `v0.9.5.124 Gold Fidelity Engine Phase 1`
- Next recommended functional sprint: `v0.9.5.126 Gold Core Blocker Triage`

## Required files for best continuation

Attach:

1. `Sentinel_v0.9.5.125.zip`
2. latest 551 screenshot pack if further validation/debugging is needed
3. latest reports if available:
   - `ground_truth_validation_report.json/xlsx`
   - `character_reocr_debug_report.json/xlsx`
   - `runtime_debug_report.json/xlsx`
   - `ocr_evidence_report.json/xlsx`
   - `inference_report.json/xlsx`

## Known latest metrics

```text
551 total_hero_power benchmark:
matched_rows: 50/50
missing_rows: 0
bad_matches: 0
recall: 100%
verified_core_identity_matches: 32
gold_core_blocker_rows: 15
row_integrity_score: 66%
runtime: ~480s CPU-only observed
```

## Highest priority next work

Do not start with more generic OCR tuning. Start with blocker triage:

1. list the 15 Gold Core blockers;
2. classify each blocker by failure class;
3. identify which are local glyph solvable;
4. identify which are policy/nonlocal script display;
5. identify which are crop geometry problems;
6. propose a safe v0.9.5.126 patch.

## Warnings

- Do not infer player continuity across pre/post transfer snapshots only from rank/power/alliance.
- Do not use historical player memory as the primary identity solution.
- Do not run Character ReOCR on context gaps.
- Do not silently convert read-only inference into Operational Truth.
