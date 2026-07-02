# Sentinel Architecture

**Version:** v0.9.5.51  
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
