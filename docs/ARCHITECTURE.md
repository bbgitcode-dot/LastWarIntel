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
