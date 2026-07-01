# Sentinel Project Status

**Current Version:** v0.9.5.46  
**Sprint Type:** Documentation Consolidation  
**Runtime Baseline:** v0.9.5.45 – Source-local Power Digit Recovery  
**Current Phase:** Data Integrity Fortress / Operational Data Stability  
**Next Planned Sprint:** v0.9.5.47 – Context-aware Power Candidate Recovery

---

## Executive summary

Sentinel is now beyond a basic OCR/export tool. The active workstream is the **Data Integrity Fortress**: every screenshot-derived observation must be guarded before it can become Operational Truth.

The recent sprint sequence from v0.9.5.40 through v0.9.5.45 hardened the Ranking Guard and Data Guard against the most dangerous class of errors: plausible-looking but false rows entering the export silently. The system now prefers quarantine or explicit recovery metadata over false confidence.

The current known limitation is narrow and well understood: **source-local leading digit recovery can detect and reduce 7xxM / 77B OCR explosions, but the current candidate choice is still too heuristic.** Example from Server 553: `764M` can be reduced to `164M`, while the screenshot truth for some rows is closer to `224M`. The next sprint should replace simple leading-digit substitution with a context-aware candidate scoring engine.

---

## What Sentinel currently does well

- Imports Last War ranking screenshots through OCR and parser layers.
- Separates runtime data from Ground Truth validation data.
- Writes operational import reports to `data/latest_import_report.json`.
- Exports Alliance Power and Total Hero Power sheets.
- Protects server assignment through Sentinel Data Guard.
- Protects ranking-type integrity through Ranking Guard.
- Quarantines uncertain rows instead of silently merging or guessing.
- Runs Ground Truth validation for development and regression analysis.
- Provides Command Center foundations for operational visibility.
- Records recovery metadata for field-level power corrections.

---

## Recent sprint history and findings

### v0.9.5.40 – Alliance Power Source-Shape Guard

**Goal:** Stop 552-style Alliance Power spikes such as `79B / 77B / 70B` from entering Operational Truth.

**Finding:** The first guard detected some high outliers but could miss clustered false high values.

**Lesson:** A single-row outlier detector is insufficient. False values can appear as a small high cluster.

---

### v0.9.5.41 – High Cluster Blocking Attempt

**Goal:** Block paired false high clusters in Alliance Power.

**Finding:** The guard still allowed some false top-cluster values while quarantining later rows.

**Lesson:** Cluster decisions must apply to the entire suspect source-local cluster, not just the last row.

---

### v0.9.5.42 – Rank / Power Envelope Guard

**Goal:** Add rank/power envelope checks to identify impossible rows.

**Finding on Server 553:** Some late-scroll THP rows were interpreted as early ranks. The guard correctly quarantined suspicious 7xxM values, but its reasoning still leaned too much on OCR rank.

**Lesson:** OCR rank is weak evidence. Power, source-local context, row shape, and screenshot segment evidence must dominate.

---

### v0.9.5.43 – THP Source-Shape Digit Explosion Guard

**Goal:** Detect 553-style `164M -> 764M` / `193M -> 793M` OCR explosions.

**Finding:** The guard correctly prevented false 700M rows from entering the export, but it preserved many useful rows only as quarantine.

**Lesson:** Some suspicious values are recoverable. Guarding and recovery must be separate responsibilities.

---

### v0.9.5.44 – Source-local Power Sanity Guard

**Goal:** Make source-local power sanity decisions independent from filename/order assumptions.

**Finding:** The system became safer, but quarantine increased. Top Alliance and THP rows were blocked when their power-to-local-median ratio was high.

**Correction:** After checking the screenshots, the apparently high top values were not legitimate; Server 553 had no true 77B alliance and no 700M player. The guard was right to block those values.

**Lesson:** Always validate assumptions against screenshot truth. A plausible game value is not automatically the screenshot truth.

---

### v0.9.5.45 – Source-local Power Digit Recovery

**Goal:** Recover safe leading-digit OCR errors instead of quarantining every suspicious row.

**Result:** The system removed the worst false values from the export:

- `7xxM` THP values were reduced to `1xxM`-scale values.
- `77B` Alliance Power was reduced to `17B`-scale values.
- The import report for Server 553 reached Ready/Healthy/0 review in the observed run.

**Remaining issue:** Candidate recovery is still too simple. It may recover `764M -> 164M` even where screenshot truth is `224M`. It may recover `77B -> 17B` where the correct value is closer to `27B` or where the row should be ranked differently.

**Lesson:** Recovery needs a candidate engine, not a single leading-digit replacement rule.

---

## Current known problems

### 1. Power candidate selection is too heuristic

**Status:** Open  
**Observed on:** Server 553  
**Confidence:** High

The system can detect that `764M` is not credible, but it does not yet reliably infer whether the best candidate is `164M`, `224M`, `174M`, or another value. The next sprint should build a candidate scoring engine.

Candidate scoring should consider:

- source-local visual context,
- neighbour powers above and below,
- ranking type,
- expected monotonic power order,
- row position within the screenshot,
- known OCR digit confusions,
- whether the candidate preserves rank order,
- whether the candidate creates duplicate or impossible values.

### 2. Recovery metadata exists but needs stronger audit value

**Status:** Partially implemented  
**Confidence:** High

v0.9.5.45 introduced fields such as `power_original`, `power_recovered_from`, and `power_recovery_method`. Future reports should also include candidate lists, selected candidate score, rejected candidate reasons, and confidence.

### 3. Import report status can be misleading

**Status:** Open  
**Confidence:** Medium

The latest Server 553 run reported Ready/Healthy/0 reviews after recovery. That is operationally useful, but it can hide that recovered values may still be wrong. Ready should eventually distinguish:

- clean trusted rows,
- trusted recovered rows,
- reviewed recovered rows,
- quarantined rows.

### 4. Screenshot segment reconstruction remains a long-term risk

**Status:** Partially mitigated  
**Confidence:** Medium

The current approach avoids relying on filename order, but true segment reconstruction is still not complete. Future imports from multiple users or mixed upload sessions require source grouping, ranking-session detection, and segment continuity checks.

---

## Current quality doctrine

```text
Parser extracts.
Data Guard protects.
Quality Loop improves source evidence.
Ranking Guard validates semantic fit.
Recovery may repair fields only when evidence is explicit.
Quarantine preserves uncertainty.
Ground Truth validates development quality.
Operational Truth must never hide uncertainty.
```

---

## Immediate next sprint recommendation: v0.9.5.47

### Focus

**Context-aware Power Candidate Recovery**

### Goal

Replace single leading-digit substitution with a candidate-based recovery engine.

### Expected outputs

- Candidate generation for suspicious THP and Alliance Power values.
- Candidate scoring based on local ranking context.
- Recovery only when one candidate is clearly stronger than alternatives.
- Quarantine when candidates remain ambiguous.
- Export/report metadata exposing original value, candidate list, selected candidate, score, and reason.
- Regression tests using Server 553 cases.

### Non-goals

- Do not expand strategic intelligence yet.
- Do not make filename order a truth source.
- Do not auto-accept ambiguous recovery.

---

## Stability exit criteria before moving to intelligence

Sentinel should not enter the next major intelligence phase until:

- No false server assignments are observed in the 549–553 regression set.
- No THP rows enter Alliance Power rankings or vice versa.
- 7xxM/77B OCR explosions are either correctly recovered or quarantined.
- Recovery reports are explainable enough for manual review.
- Ground Truth recall remains stable on the Server 551 benchmark.
- Re-running the same screenshot set produces deterministic export and report behavior.

