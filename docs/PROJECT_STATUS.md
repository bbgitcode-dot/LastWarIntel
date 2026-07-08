# Project Status – Sentinel v0.9.5.126

**Current release:** v0.9.5.126 Gold Core Blocker Triage  
**Functional baseline:** v0.9.5.126 Gold Core Blocker Triage  
**Owner:** Proud Owner  
**Copilot:** Mimir  
**Standard documentation path:** `/docs`

## Executive state

Sentinel has moved from broad OCR tuning to evidence-first data stability. The current system can find and align all 50 rows in the server 551 benchmark without missing rows or bad matches. The remaining problem is no longer basic acquisition; it is exact display fidelity for a small set of difficult identities.

The platform is now structured around guarded truth:

1. collect screenshot/Excel evidence;
2. parse and normalize;
3. guard rank/server/snapshot context;
4. verify local glyph evidence where feasible;
5. quarantine or mark review when proof is insufficient;
6. keep Operational Truth immutable unless deliberately promoted by a safe workflow.

## Latest observed benchmark state after v0.9.5.124

Server 551 `total_hero_power` ground truth validation:

```text
ground_truth_rows: 50
ocr_rows: 101
matched_rows: 50
missing_rows: 0
bad_matches: 0
recall: 1.0
precision: 0.495
verified_core_identity_matches: 32
gold_core_blocker_rows: 15
gold_core_ready: false
row_integrity_score: 66%
row_integrity_ok_rows: 33
row_integrity_review_rows: 17
character_reocr_target_count: 67
character_reocr_verified_expected: 52
character_reocr_verified_observed: 3
character_reocr_unresolved: 10
reocr_evidence_cache_hits: 11
reocr_evidence_cache_misses: 53
reocr_evidence_cache_writes: 41
reocr_evidence_cache_saved_reocr: 11
total_runtime_ms: ~480,137
```

Interpretation: the acquisition and matching layer is stable; the remaining risk sits in Gold Core display blockers and multilingual/local glyph proof.

## What the last sprint chain achieved

### DataGuard and Ranking Guard

The project hardened the rule that unsafe rows are not silently accepted. Ranking Guard blocks fallback when rank/power/name context is ambiguous. DataGuard prefers quarantine and review over false Operational Truth.

### Context Gap Handling

Rows such as `K9 Thunder`, `HUNI`, and hangul-only cases can land in context gaps where the surrounding rank/power trend supports read-only inference but the actual OCR row is unsafe. Sentinel now treats these as contextual inference, not character drift.

Current rule: context gaps must not enter Character ReOCR. A mismatch like `K9 Thunder` vs `YUNS` is not a glyph typo; it is an alignment/context problem until proven otherwise.

### Character ReOCR

Character ReOCR evolved from broad expensive rereads into targeted screenshot-local glyph evidence. It is useful for local confusions such as:

- `Joncollinszl` -> `Joncollins21`;
- `PBC` -> `PbC` when the tag block proves the case-sensitive glyph;
- `Pumpkin 6` -> `Pumpkin G`;
- `Oisneys Mushu` -> `Disneys Mushu`.

It remains intentionally limited. It does not solve broad multilingual replacement spans, unknown names, or row-context gaps.

### Evidence Inspector and Row Integrity

The Evidence Inspector introduced row-level statuses such as:

- `ROW_OK_NO_REOCR`;
- `ROW_OK_POLICY_BUDGET`;
- `ROW_OK_POLICY_NONLOCAL`;
- `ROW_OK_WITH_CROP_WARNING`;
- `ROW_OK_WITH_VOTE_WARNING`;
- `ROW_CONTEXT_GAP`;
- `ROW_REOCR_UNRESOLVED`;
- `ROW_VOTE_OUTSIDE_ALLOWED_SET`;
- `ROW_FIELD_MISMATCH_DIAGNOSTIC`.

This shifted the project from “OCR was wrong” to “which evidence class failed?”

### Gold Fidelity Engine Phase 1

v0.9.5.124 introduced a conservative snapshot-local ReOCR Evidence Cache. It reuses only decisive `verified_expected` / `verified_observed` outcomes for exact target/text pairs inside the same validation run. It does not use a historical player database and does not change Operational Truth.

The latest observed runtime dropped to roughly 8 minutes while preserving 50/50 matched rows and 0 bad matches.

## Current blockers

The next functional sprint should focus on the remaining 15 Gold Core blockers. Current blocker classes include:

- `ROW_VOTE_OUTSIDE_ALLOWED_SET` where selected evidence may already prove the expected glyph but noisy votes keep the row blocked;
- `ROW_REOCR_UNRESOLVED` where local targets remain unreadable;
- `ROW_OBSERVED_TEXT_CONFIRMED` where ReOCR confirmed the OCR text instead of ground truth;
- `ROW_POLICY_NONLOCAL_REVIEW` for multilingual/nonlocal display drift;
- `ROW_FIELD_MISMATCH_DIAGNOSTIC` where crop geometry remains suspect.

## Recommended next sprint

**v0.9.5.127 – Local Glyph Resolution Hardening**

Primary goals:

1. Produce a dedicated list of the 15 Gold Core blockers with rank, expected/observed/verified display, status, reason, and next action.
2. Split blockers into solvable local glyph issues, nonlocal script-display issues, crop geometry issues, and true manual review cases.
3. Downgrade `vote_outside_allowed_set` to warning when selected glyph equals expected, confidence is high, and Core Identity is otherwise verified.
4. Keep `ROW_OBSERVED_TEXT_CONFIRMED` strict because it is evidence against the expected display.
5. Improve cache summary visibility in top-level reports.

## Information needed for complete handover

A complete future handover should include:

- latest Sentinel ZIP;
- latest 551 screenshot pack or equivalent benchmark pack;
- latest `ground_truth_validation_report.json/xlsx`;
- latest `character_reocr_debug_report.json/xlsx`;
- latest `runtime_debug_report.json/xlsx`;
- latest `ocr_evidence_report.json/xlsx`;
- current active snapshot name/id;
- exact command used for validation;
- whether `main.py` was rerun or only `ground_truth_validator.py` was run;
- Python version and whether CPU-only EasyOCR was used.


## v0.9.5.126 update

The Gold Core blocker triage report is now generated by the validator as `gold_core_blocker_report.json` and `gold_core_blocker_report.xlsx`. It lists each active `gold_core_blocker` row and classifies it into a safe fix lane: local glyph, mixed local/nonlocal, nonlocal script policy, crop geometry, observed-text-confirmed, vote-warning gate review, context gap, or manual review.

This is diagnostic only. It does not promote read-only inference, mutate Operational Truth, or treat historical identity memory as evidence.
