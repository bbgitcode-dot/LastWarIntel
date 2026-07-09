# Sentinel Architecture

**Current version:** v0.9.5.125  
**Functional baseline:** v0.9.5.124 Gold Fidelity Engine Phase 1

Sentinel is an explainable strategic intelligence platform for Last War. The current architecture is evidence-first: it prioritizes stable acquisition, protected Operational Truth, and auditable validation before strategic assessment.

## High-level flow

```text
Screenshot / Excel / Manual Source
        ↓
Import Context / Managed Snapshot
        ↓
OCR or Structured Import
        ↓
Parsing and Normalization
        ↓
Ranking Guard + Data Guard
        ↓
Recovery / Quarantine / Review Evidence
        ↓
Ground Truth Validation and Evidence Inspector
        ↓
Operational Truth / Export / Historical Reference
        ↓
Command Center / Strategic Intelligence Layer
```

## Core layers

### 1. Snapshot layer

A managed snapshot binds screenshot imports to a collection context. It is not truth by itself. It provides scope, expected servers/rankings, lifecycle state, and audit metadata.

### 2. OCR and parser layer

The parser converts screenshot evidence into candidate rows. OCR output is evidence, not automatically truth.

### 3. Ranking Guard

Ranking Guard protects against row contamination, N+1 assumptions, unsafe fallback, and ambiguous rank/power recovery. It can quarantine rows instead of accepting unsafe matches.

### 4. DataGuard

DataGuard protects Operational Truth. It marks uncertainty, blocks unsafe promotion, and preserves reviewability.

### 5. Contextual inference

Inference can accept bounded gaps as read-only context when neighboring ranks and power trends support the expected row. It must not mutate Operational Truth.

### 6. Character ReOCR

Character ReOCR provides screenshot-local glyph evidence for specific targets. It is useful for local confusions and case-sensitive tags. It is not used for broad context gaps or nonlocal multilingual replacement spans.

### 7. Evidence Inspector

The Evidence Inspector explains row integrity and ReOCR provenance. It classifies rows into OK, warning, review, unresolved, and context-gap categories.

### 8. Gold Fidelity Engine Phase 1

The Gold Fidelity Engine begins with snapshot-local ReOCR evidence caching. It reuses decisive glyph evidence only for exact target/text pairs within the same validation run. It is not a historical identity database.

## Current architecture boundary

Sentinel currently separates:

- **Core Identity:** enough evidence for operational row identity.
- **Display Fidelity:** exact player/tag spelling.
- **Gold Fidelity:** exact/screenshot-proven display, rank, power, and identity.
- **Operational Truth:** downstream truth store protected by DataGuard.

This separation is essential for safe pre/post transfer analysis.

## v0.9.5.128 Architecture Note – Alignment Intelligence

The validation pipeline now includes an Alignment Intelligence layer after contextual inference and before reporting. It scores structural evidence for context gaps and emits read-only verification eligibility fields: `alignment_score`, `alignment_score_evidence`, `verification_allowed_read_only`, `verification_block_reason`, and `read_only_verification_status`.
## v0.9.5.129 Road-to-V1 Update – Read-only Evidence Execution

The Alignment Intelligence lane now executes evidence-only verification for eligible Context Gap rows. This improves explainability without weakening DataGuard. The next V1-critical step is not automatic correction; it is an explicit evidence consumption policy that separates review recommendations from Operational Truth.



## v0.9.5.131 Architecture Note – Display Reconstruction Engine

The validator now has a read-only Display Reconstruction stage after Alignment Guard and Character ReOCR evidence collection. This stage consumes evidence and emits display proposals; it does not mutate any operational identity field.

Pipeline position:

```text
OCR Export
  -> Ranking Guard
  -> Context Inference / Alignment Guard
  -> Character ReOCR Evidence
  -> Display Reconstruction Report
  -> DataGuard / Gold policy review
```

This keeps Evidence before Inference intact while making evidence useful for human review and future Gold Display exports.

## v0.9.5.133 Architecture Addendum – Evidence Confidence Engine

The Display Fidelity pipeline now includes an Evidence Confidence stage:

```text
Character ReOCR Evidence
        ↓
Fragment Confidence
        ↓
Evidence Coverage Score
        ↓
Display Reconstruction Guard
        ↓
Report-only Display Proposal
```

The engine scores fragment quality using crop quality, OCR confidence, vote consensus, position stability, unicode/script class and status weight. These scores are diagnostic and can only make promotion more conservative.


## v0.9.5.134 – Evidence Budget Manager

This release adds a read-only Evidence Budget Manager for Display Fidelity. The new budget layer scores display reconstruction candidates before future expensive ReOCR work is promoted into the active pipeline. It introduces `evidence_priority_score`, `evidence_budget_tier`, `evidence_budget_action`, `evidence_budget_reason`, and the standalone `evidence_budget_report.json/xlsx`.

The sprint does not change Operational Truth, snapshots, exports, Ground Truth, or DataGuard policy. Its purpose is to make future Character ReOCR investment explainable and selective: high-value candidates can receive full budget, medium candidates receive targeted budget, weak evidence is blocked early or served from cache.
