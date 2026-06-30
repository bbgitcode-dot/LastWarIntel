# Sentinel Architecture

> **Version:** v0.9.5.27  
> **Status:** Living Document

---

## Purpose

Sentinel is a strategic intelligence platform. Its architecture is designed around one principle:

> **Operational truth before strategic intelligence.**

A recommendation is only useful if the observations underneath it are reliable, traceable, and explainable.

---

## High-level architecture

```text
Presentation
────────────────────────────────────────────
Command Center
REST API
Reports

                ▲
                │
Application / Operations
────────────────────────────────────────────
Operational Import Service
Data Quality Service
Command Center Service
Review / Quarantine Views

                ▲
                │
Inference Layer
────────────────────────────────────────────
Context Engine
Evidence-based Inference Reports
Read-only validation conclusions

                ▲
                │
Integrity Layer
────────────────────────────────────────────
Sentinel Data Guard
Sentinel Data Quality Loop
Recovery Advisor
Sentinel Ranking Guard
Evidence Resolver (validation/inference)

                ▲
                │
Core Data Processing
────────────────────────────────────────────
OCR Provider
Parser
Normalizer
Ranking Parser
Ground Truth Validator (development only)

                ▲
                │
Persistence / Runtime Data
────────────────────────────────────────────
Operational Import Report
SQLite
Future Repository Layer
Future PostgreSQL
```

---

## Data flow

```text
Screenshot
    ↓
OCR pass 1
    ↓
Parser / Normalizer
    ↓
Sentinel Data Guard
    ├── pass → Import
    └── uncertain → Data Quality Loop
                         ↓
                   Targeted Recovery
                         ↓
                   OCR retry
                         ↓
                   Data Guard recheck
                         ↓
                   Import or Quarantine
```

---

## Sentinel Data Guard

The Data Guard protects runtime truth.

Responsibilities:

- Validate server assignment.
- Detect server assignment conflicts.
- Prefer intrinsic screenshot evidence over file metadata.
- Quarantine suspicious blocks instead of silently merging them.
- Explain why a block is trusted, rejected, or quarantined.

Non-responsibilities:

- It must not guess.
- It must not auto-merge conflict blocks into another ranking.
- It must not use filename timestamps as decision evidence.
- It must not replace the parser or validator.

---

## Sentinel Data Quality Loop

The Data Quality Loop is the recovery layer between Data Guard and human review.

Responsibilities:

- Run targeted OCR recovery attempts.
- Improve source evidence through image preprocessing.
- Log recovery attempts and confidence changes.
- Stop after a bounded number of attempts.
- Return recovered evidence to Data Guard for validation.

Design principle:

> **Recover evidence, do not invent truth.**

Current recovery focus:

- Server/header evidence.
- Image enhancement using crop, CLAHE, upscaling, sharpening, and thresholding.

Long-term design:

The Quality Loop must become field-based:

```text
Recovery Advisor
    ├── Server Recovery
    ├── Alliance Tag Recovery
    ├── Player Name Recovery
    ├── Hero Power Recovery
    ├── Alliance Power Recovery
    ├── Rank Recovery
    └── Ranking Type Recovery
```

---

## Ground Truth boundary

Ground Truth is a development and benchmarking tool.

Correct boundary:

```text
Ground Truth validates Sentinel.
Repositories and operational reports power Sentinel.
```

Runtime application components must not depend on `ground_truth_validation_report.json`.

---

## Current known architecture gap

The latest import test proved that server assignment can now be protected, but ranking-type contamination still exists.

Example class of issue:

- THP-like rows enter `alliance_power`.
- Alliance Power rows are accepted even when value ranges and required fields do not fit the ranking type.

Planned fix:

## v0.9.5.25 – Sentinel Ranking Guard

Status: implemented as a modular runtime guard in `parser/ranking_guard.py`.

Responsibilities:

- Validate that each row belongs to the assigned ranking type.
- Reject or quarantine THP rows inside Alliance Power rankings.
- Reject or quarantine Alliance Power rows inside THP rankings.
- Validate expected value ranges, required fields, player/alliance row shape, and quarantine semantic mismatches before merge/export.

---

## Evidence Resolver boundary

The Evidence Resolver introduced in v0.9.5.27 is a validation/inference component, not a runtime mutation layer.

Responsibilities:

- Resolve recoverable Ground Truth gaps when observed export evidence is strong enough.
- Prefer unique exact THP power as a row anchor.
- Require additional identity evidence for near or repaired power matches.
- Mark recovered rows with explicit `gap_*` match methods in validation reports.

Non-responsibilities:

- It must not rewrite exports.
- It must not override Data Guard or Ranking Guard.
- It must not turn rank-only contradiction into accepted truth.

Operational rule:

```text
Observed export data remains Operational Truth.
Evidence Resolver output is inferred validation evidence.
```

## Layer rules

1. Presentation displays results. It does not decide.
2. Application services coordinate use cases. They do not parse screenshots.
3. Data Guard protects integrity. It does not repair data silently.
4. Quality Loop attempts recovery. It does not decide truth.
5. Parser extracts structure. It does not produce strategic intelligence.
6. Ground Truth benchmarks. It does not power runtime.
7. Strategic Intelligence consumes trusted observations only.


## Inference Layer

The Inference Layer operates above Operational Truth. It does not modify parser rows, exports, Data Guard decisions, or Ranking Guard decisions. Its responsibility is to derive explicit, explainable conclusions from validated evidence.

First capability in v0.9.5.28:

- Context Engine for bounded local ranking gaps.
- Evidence-based confidence scoring.
- Separate inference reports for auditability.

Layer rule:

```text
Operational Truth is observed and guarded.
Inference is derived and explained.
```


## Universal Server Detection

Server assignment now uses pattern-first OCR evidence before language-specific labels. Repeated row-level `#server` candidates, such as mobile screenshots showing `#552` on each ranking row, are collected and passed into the existing consensus/Data Guard path. This preserves the doctrine: intrinsic screenshot evidence wins, but ambiguous or insufficient evidence remains review-only.
