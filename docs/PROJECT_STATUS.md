# Project Status – Sentinel v0.9.5.89

**Current baseline:** Sentinel v0.9.5.88 Documentation Consolidation & Handoff  
**Current sprint:** v0.9.5.89 Non-cache Data Quality Validation & Rank Slot Regression  
**Canonical docs path:** `/docs`  
**Operating roles:** Mimir = strategic copilot; Proud Owner = product owner and acceptance authority.

## Executive state

Sentinel remains in the **Data Quality before Intelligence** phase. v0.9.5.89 is a targeted engineering sprint after the v0.9.5.88 documentation consolidation. It does not expand strategic intelligence. It hardens the protected path from screenshot observation to reviewable Operational Truth.

The sprint focus is narrow:

1. keep data-quality validation cache-off by default;
2. preserve rank slots when rows are pending review or quarantined;
3. expose raw observed identity and pending-slot state in Excel exports;
4. add regression coverage for `Sven the vän`, `[SWSq]`, quarantined rank slots and low-truncation recovery behavior.

## What changed in v0.9.5.89

### Export fidelity for pending slots

Excel export columns now include the fields needed to audit pending/quarantined rows in their original visible slot:

```text
pending_review
pending_review_reason
rank_slot_preserved
observed_name
normalized_name
canonical_name
observed_alliance
normalized_alliance
canonical_alliance
```

This closes a practical review gap: the internal pipeline already carried pending-slot state, but exports could hide the important distinction between observed evidence, normalized identity and canonical identity.

### Regression coverage

Added `tests/smoke/test_data_quality_89.py` covering:

- development-mode cache-off defaults;
- Ranking Guard placeholder behavior preserving rank 10 while ranks 11 and 12 remain unchanged;
- raw display fidelity for `Sven the vän` / `[SWSq]` on power-recovery placeholders;
- Excel export of pending slot state and observed identity.

Updated recognition-quality smoke expectations to the current telemetry version while preserving the v0.9.5.87 power-recovery decision version for unchanged recovery logic.

## Current risks

1. **Full smoke collection debt:** the whole `tests/smoke` collection still contains legacy invalid test files and stale OCR-config imports unrelated to this sprint. Targeted validation passes; full collection stops during collection.
2. **Rank-slot drift:** still remains a P0 class. Any future export/report path that omits pending slots can create false rank continuity.
3. **Identity fidelity:** observed fields must remain human-facing until a reviewer chooses a canonical identity.
4. **Cache masking:** benchmark recognition work must run with cache disabled unless the explicit purpose is cache/performance validation.
5. **Review lifecycle debt:** current/stale/resolved reviews still need a dedicated cleanup sprint.

## Immediate next engineering priorities

### P0 – Clean smoke-test collection

Fix or quarantine legacy smoke files that are not valid pytest modules and stale OCR-config import tests. Sentinel needs a reliable full smoke command before v1.

### P0 – Run 549–554 non-cache benchmark

Use the 549–554 screenshot pack with OCR cache disabled. Verify:

- cache hits remain zero;
- `Sven the vän` / `[SWSq]` are visible as observed evidence;
- quarantined rows do not collapse subsequent ranks;
- Excel exports and HTML reports agree on pending rank slots;
- power recovery families remain explainable.

### P0 – Report/export parity

After the Excel export fix, verify that Command Center, Review Dashboard and Evidence Pack also surface pending-slot state consistently.

## Acceptance philosophy

Sentinel should prefer:

```text
missing / pending / review
```

over:

```text
plausible but false Operational Truth
```

This remains the main product principle until v1.0.0.
