# NEXT_CHAT – Sentinel Handover

## Start prompt for the next chat

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

Aktuelle Basis ist Sentinel_v0.9.5.127.zip.
Bitte lies zuerst /docs/PROJECT_STATUS.md, /docs/ROAD_TO_V1.md, /docs/MODUS_OPERANDI.md, /docs/SENTINEL_DATA_GUARD.md, /docs/LESSONS_LEARNED.md und /docs/PATCH_SUMMARY.md.

Nächster empfohlener Sprint ist v0.9.5.128 – Safe Warning Downgrade & Local Glyph Retry.
Ziel: die in v0.9.5.127 erzeugten Gold-Core-Resolution-Actions verwenden, um nur sichere lokale Kandidaten zu bearbeiten. Keine generische OCR-Optimierung, keine Character ReOCR auf Context Gaps, keine Operational-Truth-Mutation.
```

## Current release

- Current release: `v0.9.5.127 Gold Core Resolution Plan`
- Functional baseline: `v0.9.5.126 Gold Core Blocker Triage`
- Next recommended functional sprint: `v0.9.5.128 Safe Warning Downgrade & Local Glyph Retry`

## Required files for best continuation

Attach:

1. `Sentinel_v0.9.5.127.zip`
2. latest 551 screenshot pack if further validation/debugging is needed
3. latest reports if available:
   - `ground_truth_validation_report.json/xlsx`
   - `gold_core_blocker_report.json/xlsx`
   - `gold_core_resolution_plan_report.json/xlsx`
   - `character_reocr_debug_report.json/xlsx`
   - `ocr_evidence_report.json/xlsx`
   - `inference_report.json/xlsx`
   - `runtime_debug_report.json/xlsx`

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
runtime: ~423s validator total, CPU-only observed
```

## v0.9.5.127 resolution summary

```text
P1_WARNING_DOWNGRADE_BLOCKED_BY_CORE: 5 rows
P2_SCRIPT_POLICY_REQUIRED: 2 rows
P1_LOCAL_GLYPH_RETRY: 1 row
P1_CROP_GEOMETRY_FIRST: 3 rows
P2_MANUAL_BENCHMARK_REVIEW: 3 rows
P1_SPLIT_LOCAL_FROM_SCRIPT: 1 row
```

## Highest priority next work

1. Use `gold_core_resolution_plan_report` as source of truth for next engineering action.
2. Implement actual resolver only for `P1_LOCAL_GLYPH_RETRY` first.
3. Consider warning downgrade only for rows that become `P1_WARNING_DOWNGRADE_SAFE`.
4. Keep crop geometry, nonlocal script, observed-text-confirmed, and context-gap rows blocked.
5. Measure blocker reduction without allowing new bad matches.

## Warnings

- Do not infer player continuity across pre/post transfer snapshots only from rank/power/alliance.
- Do not use historical player memory as the primary identity solution.
- Do not run Character ReOCR on context gaps.
- Do not silently convert read-only inference into Operational Truth.
- Do not downgrade vote warnings when Core Identity is not independently proven.

## Next Recommended Sprint after v0.9.5.128

Recommended next sprint: `v0.9.5.129 – Read-Only Evidence Execution`. Start from `alignment_intelligence_report.json/xlsx`. Implement actual read-only evidence collection for rows with `verification_allowed_read_only=true`, but keep Operational Truth, exports, snapshots, and Ground Truth immutable.
## v0.9.5.129 Road-to-V1 Update – Read-only Evidence Execution

The Alignment Intelligence lane now executes evidence-only verification for eligible Context Gap rows. This improves explainability without weakening DataGuard. The next V1-critical step is not automatic correction; it is an explicit evidence consumption policy that separates review recommendations from Operational Truth.



## Current handoff after v0.9.5.131

Current release: `Sentinel_v0.9.5.131.zip`

Implemented: Display Reconstruction Engine Phase I.

Next recommended sprint: `v0.9.5.132 – Display Reconstruction Evaluation`.

Start by reading:

- `display_reconstruction_report.json/xlsx` from the next run
- `ground_truth_validation_report.json/xlsx`
- `character_reocr_debug_report.json/xlsx`
- `gold_core_blocker_report.json/xlsx`

Main question for `.132`: Which reconstructed display proposals are safe report-only wins, which rows remain crop geometry problems, and which require multilingual/nonlocal script policy?

## Handoff after v0.9.5.132

Current release: `Sentinel_v0.9.5.132.zip`.

Next recommended sprint: `v0.9.5.134 – Crop Geometry Optimizer`.

Rationale: `.132` prevents unsafe display promotion. The next bottleneck is better evidence collection: crop bleed, anchor mismatch, and low-coverage character fragments still limit Display Fidelity.

## Handoff after v0.9.5.134

Current release: `Sentinel_v0.9.5.134.zip`.

Implemented:
- Evidence Confidence Engine
- Fragment confidence scoring
- Display coverage scoring
- `evidence_confidence_report.json/xlsx`

Next recommended sprint: `v0.9.5.134 – Crop Geometry Optimizer`.


Next recommended sprint: v0.9.5.135 – Evidence Budget Execution / Runtime Reduction.
Attach the latest `evidence_budget_report.json/xlsx`, `evidence_confidence_report.json/xlsx`, and runtime reports.
