**Version:** v0.9.5.54  

## v0.9.5.54 Contextual Row Reconstruction Architecture

Sentinel now treats Review as a two-stage remediation layer:

```text
Ranking Guard / Power Guard
→ Adaptive Review OCR
→ Contextual Row Reconstruction
→ Promote only on bounded source-local evidence
→ otherwise keep quarantine
```

Adaptive Review OCR improves direct row evidence through crop variants. Contextual Row Reconstruction handles the class of failures where OCR remains weak but a low/truncated THP row is bounded by trusted source-local anchor powers in the same screenshot. The reconstruction layer is intentionally narrow and does not use filename order, upload order, or cross-screenshot sequence as truth.

Report metadata now exposes reconstruction status, anchor powers, reconstructed rank, method, score, and reason so promoted rows stay explainable.

**Version:** v0.9.5.53  

## v0.9.5.53 Review OCR Architecture

Sentinel now includes an adaptive Review OCR stage after Ranking Guard and Power Sanity Guard. The stage operates only on rows already isolated for review. It uses source-local visual evidence: original screenshot, row y-position, deterministic crop variants, 2x zoom, CLAHE, and sharpen. The stage may promote a row only when the re-OCR candidate passes a conservative evidence gate.

Flow:

```text
Ranking Guard / Power Guard
→ Quarantine candidate
→ Adaptive Review OCR
→ Promote on strong direct OCR evidence
→ otherwise keep quarantine
```

This keeps Operational Truth protected while using review as a quality-improvement opportunity.


# Sentinel Architecture

**Version:** v0.9.5.52  
**Status:** Living Document

---

## Purpose

Sentinel is an explainable strategic intelligence platform for Last War. Its architecture is built around one principle:

> Operational truth before strategic intelligence.

Recommendations are only useful when the observations underneath them are reliable, traceable, and explainable.

---

## High-level architecture

```text
Presentation
────────────────────────────────────────────
Command Center
REST API
Reports

Application / Operations
────────────────────────────────────────────
Operational Import Service
Data Quality Service
Import Report Repository
Review / Quarantine Views

Integrity Layer
────────────────────────────────────────────
Sentinel Data Guard
Ranking Guard
Power Sanity Guard
Recovery Advisor
Sentinel Data Quality Loop

Core Data Processing
────────────────────────────────────────────
OCR Provider
Parser
Normalizer
Ranking Parser
Power Recovery
Ground Truth Validator (development only)

Persistence / Runtime Data
────────────────────────────────────────────
Operational Import Report
SQLite
Future Snapshot Repository
Future PostgreSQL
```

---

## Data flow

```text
Screenshot
    ↓
OCR pass
    ↓
Parser / Normalizer
    ↓
Ranking Parser
    ↓
Data Guard and Ranking Guard
    ├── trusted → Import / Export
    ├── recoverable → Field Recovery → Guard recheck
    └── uncertain → Quarantine / Review
```

---

## Component responsibilities

### Parser

Extracts structure from OCR observations. It does not decide strategic truth and does not silently repair ambiguous data.

### Sentinel Data Guard

Protects server and data integrity. It validates, blocks, explains, and quarantines. It must not guess server assignment or use filenames and timestamps as truth.

### Ranking Guard

Validates whether rows belong to the assigned ranking type. It protects against THP rows entering Alliance Power and Alliance Power rows entering THP.

### Power Sanity Guard

Validates source-local power plausibility. It detects digit explosions such as false `7xxM` THP values or false `77B` Alliance Power values.

### Recovery Layer

May repair a field only when evidence is explicit and auditable. Recovery must preserve original values and method metadata. It must not invent truth.

### Sentinel Data Quality Loop

Attempts to improve source evidence through targeted OCR strategies. It recovers evidence, not truth.

### Ground Truth Validator

Development and benchmarking tool only. Ground Truth validates Sentinel; it does not power runtime.

---

## Critical architecture rules

1. Intrinsic screenshot evidence beats filenames and timestamps.
2. Screenshot order must never be treated as truth.
3. Guarding and recovery are different responsibilities.
4. Quarantine is a valid outcome, not a failure.
5. Recovered rows must remain auditable.
6. Runtime data must not depend on Ground Truth artifacts.
7. Strategic intelligence consumes only trusted or explicitly accepted data.

---

## Current architecture gap

v0.9.5.48 made context-aware power recovery reportable. Recovered and ambiguous rows now carry candidate metadata in both Excel exports and the operational import report.

The next architecture gap is explicit import-session and segment integrity so mixed screenshot batches can be validated without relying on filename or upload order.

Recovery remains source-local and auditable:

```text
764M → candidates [164M, 224M, 174M, 264M]
       → score against local row context
       → recover clear winner or quarantine ambiguity
       → export/report candidate trace
```


## Current recovery decision model

v0.9.5.51 removes the final legacy leading-digit recovery fallback. Power recovery now follows a candidate-decision model:

```text
Suspicious power value
    ↓
Candidate generation
    ↓
Context scoring
    ↓
Margin threshold
    ├── clear winner → recovered with audit metadata
    └── tied/weak winner → quarantine
```

The recovery layer may still generate candidates from known OCR digit confusions, but it may not select a candidate without a clear score margin.


## v0.9.5.51 recovery extension

The recovery layer now treats OCR power errors as bidirectional. High explosions (`798M -> 198M`) and low truncations (`32M -> 320M`) both enter the same candidate-decision engine. Candidate generation is ranking-type aware, source-local, and margin-gated. Ground Truth does not power runtime decisions.


## v0.9.5.52 recovery extension

The recovery decision engine now includes two explicit guardrails:

1. **Segment-order tie-breaker** – for close high-explosion THP candidates only, a candidate that better preserves prior/following rank order may be selected if the score gap is small and no order break exists.
2. **Conservative low-truncation gate** – low/truncated THP recovery requires stronger digit preservation and candidate margin evidence. If `scale_x10` and `insert_zero` remain too close, the row is quarantined.

These guardrails are intentionally source-local. They do not use screenshot filename order, upload order, or Ground Truth as runtime truth.

